from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .artifacts import output_url, write_export_bundle
from .pipeline import build_preview_result
from .contracts import TakeoffRequest
from .optimizer import build_optimization_plan
from .workbook import build_workbook_template


def _job_id() -> str:
    return datetime.now(timezone.utc).strftime("job_%Y%m%d_%H%M%S")


def _detect_file_type(path: str) -> str:
    suffix = Path(path).suffix.lower()
    if suffix == ".pdf":
        return "pdf"
    if suffix == ".dwg":
        return "dwg"
    if suffix == ".dxf":
        return "dxf"
    return "unknown"


def _ok(payload: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    return 200, payload


def _error(status: int, code: str, message: str, fallbacks: List[Dict[str, Any]] | None = None) -> Tuple[int, Dict[str, Any]]:
    return status, {
        "ok": False,
        "error": {"code": code, "message": message},
        "fallbacks": fallbacks or [],
    }


def _enforce_cost_guardrails(payload: Dict[str, Any], total_pages: int | None) -> Tuple[List[Dict[str, Any]], Tuple[int, Dict[str, Any]] | None]:
    limits = payload.get("cost_limits") or {}
    usage = payload.get("usage") or {}
    warnings: List[Dict[str, Any]] = []
    if not limits and not usage:
        return warnings, None

    ocr_cap_pct = float(limits.get("ocr_page_cap_pct", 0.15))
    vision_cap_pct = float(limits.get("vision_page_cap_pct", 0.05))
    storage_cap_mb = float(limits.get("storage_cap_mb", 200.0))
    total_pages = usage.get("total_pages", total_pages)

    if total_pages is None:
        warnings.append({"code": "missing_total_pages", "message": "Total pages required for OCR/vision caps."})
    else:
        ocr_pages = usage.get("ocr_pages")
        if ocr_pages is None:
            warnings.append({"code": "missing_ocr_usage", "message": "OCR page usage not provided."})
        elif total_pages > 0 and (ocr_pages / total_pages) > ocr_cap_pct:
            return warnings, _error(
                429,
                "ocr_page_cap_exceeded",
                "Requested OCR pages exceed the configured cap.",
                [{"action": "reduce_ocr_scope"}, {"action": "request_override"}],
            )

        vision_pages = usage.get("vision_pages")
        if vision_pages is None:
            warnings.append({"code": "missing_vision_usage", "message": "Vision page usage not provided."})
        elif total_pages > 0 and (vision_pages / total_pages) > vision_cap_pct:
            return warnings, _error(
                429,
                "vision_page_cap_exceeded",
                "Requested vision pages exceed the configured cap.",
                [{"action": "disable_vision"}, {"action": "request_override"}],
            )

    storage_mb = usage.get("storage_mb")
    if storage_mb is not None and storage_mb > storage_cap_mb:
        return warnings, _error(
            429,
            "storage_cap_exceeded",
            "Estimated storage exceeds the configured cap.",
            [{"action": "reduce_cache"}, {"action": "request_override"}],
        )

    return warnings, None


def intake_prepare(payload: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    files = payload.get("files")
    if not isinstance(files, list) or not files:
        return _error(400, "files_required", "At least one input file is required.")
    inputs = []
    warnings = []
    for file_path in files:
        file_type = _detect_file_type(file_path)
        if file_type == "unknown":
            warnings.append({"code": "unsupported_extension", "file": file_path})
        pages = 12 if file_type == "pdf" else None
        item = {"file": Path(file_path).name, "type": file_type}
        if pages is not None:
            item["pages"] = pages
        inputs.append(item)
    return _ok({"ok": True, "job_id": _job_id(), "inputs": inputs, "warnings": warnings})


def extract_dwg(payload: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    file_path = payload.get("file", "")
    file_type = _detect_file_type(file_path)
    if file_type not in {"dwg", "dxf"}:
        return _error(400, "dwg_file_required", "DWG or DXF input is required.")
    
    source_path = Path(file_path) if file_path else None
    if source_path is not None and ("/" in file_path or "\\" in file_path):
        if not source_path.exists():
            return _error(404, "source_file_missing", f"Uploaded source file not found: {file_path}")
            
    try:
        from .extractor_dxf import extract_dxf_entities
        scale_factor = float(payload.get("scale", {}).get("scale_factor", 0.001))
        real_path = str(source_path) if source_path else file_path
        extraction = extract_dxf_entities(real_path, scale_factor=scale_factor)
    except Exception as e:
        return _error(
            422,
            "vector_extraction_failed",
            f"DXF vector extraction failed: {e}",
            [
                {"action": "review_source_file"},
                {"action": "adjust_scale_or_layer_mapping"},
            ],
        )

    entities = extraction["entities"]
    metrics = extraction["metrics"]
    review_queue = extraction["review_queue"]
    warnings: List[Dict[str, Any]] = []
    if metrics["generic_entities"] > 0:
        warnings.append(
            {
                "code": "unknown_layer_block",
                "message": f"{metrics['generic_entities']} entities not mapped; assigned to Unclassified bucket.",
                "fallback": "prompt user mapping and store template",
            }
        )
    if metrics["unresolved_area_entities"] > 0:
        warnings.append(
            {
                "code": "unresolved_vector_area",
                "message": f"{metrics['unresolved_area_entities']} entities require manual review for area resolution.",
                "fallback": "manual review queue",
            }
        )

    mapped_count = metrics["kept_entities"] - metrics["generic_entities"]
    return _ok(
        {
            "ok": True,
            "mode": "vector_ezdxf",
            "entities": entities,
            "warnings": warnings,
            "review_queue": review_queue,
            "metrics": metrics,
            "entity_count": metrics["kept_entities"],
            "mapped_count": mapped_count,
            "generic_count": metrics["generic_entities"],
            "resolved_file": str(source_path) if source_path else file_path,
        }
    )


def extract_pdf(payload: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    file_path = payload.get("file", "")
    scale = payload.get("scale")
    if not scale:
        return _error(
            422,
            "missing_scale",
            "PDF extraction requires calibration before processing.",
            [
                {"action": "manual_scale_entry", "options": ["ratio", "known_distance"]},
                {"action": "block_extraction", "reason": "scale_required"},
            ],
        )
    vision = payload.get("vision", {})
    if vision.get("requested") and not vision.get("approved"):
        return _error(
            403,
            "vision_approval_required",
            "Vision inference requires explicit approval when low-cost mode is enabled.",
            [{"action": "approve_vision"}, {"action": "continue_without_vision"}],
        )
    total_pages = payload.get("total_pages", 1)
    guardrail_warnings, guardrail_error = _enforce_cost_guardrails(payload, total_pages)
    if guardrail_error:
        return guardrail_error

    source_path = Path(file_path) if file_path else None
    if source_path is not None and ("/" in file_path or "\\" in file_path):
        if not source_path.exists():
            return _error(404, "source_file_missing", f"Uploaded source file not found: {file_path}")

    try:
        from .extractor_pdf import extract_pdf_entities
        scale_factor = float(scale.get("scale_factor", 0.05))
        real_path = str(source_path) if source_path else file_path
        extraction = extract_pdf_entities(real_path, scale_factor=scale_factor)
    except Exception as e:
        return _error(
            422,
            "vector_extraction_failed",
            f"PDF vector extraction failed: {e}",
            [
                {"action": "review_source_file"},
                {"action": "adjust_scale"},
            ],
        )
        
    entities = extraction["entities"]
    metrics = extraction["metrics"]
    review_queue = extraction["review_queue"]
    
    warnings: List[Dict[str, Any]] = list(guardrail_warnings)
    if metrics["raster_pages"] > 0:
        warnings.append({
            "code": "raster_pages_detected",
            "message": f"Detected {metrics['raster_pages']} raster/scanned pages. These require Vision/OCR for takeoffs.",
            "fallback": "prompt_vision_approval"
        })

    return _ok(
        {
            "ok": True,
            "mode": "vector_pdfplumber",
            "entities": entities,
            "warnings": warnings,
            "review_queue": review_queue,
            "metrics": metrics,
            "entity_count": metrics["kept_entities"],
            "generic_count": metrics["generic_entities"],
            "resolved_file": str(source_path) if source_path else file_path,
        }
    )


def map_schema(payload: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    entities = payload.get("entities", [])
    symbol_map = payload.get("symbol_map", {})
    mapped = []
    warnings = []
    for idx, entity in enumerate(entities, start=1):
        if isinstance(entity, dict):
            entity_id = entity.get("id", f"ent_{idx:03d}")
        else:
            entity_id = str(entity)
        mapped.append(
            {
                "id": f"ELEM-{idx:03d}",
                "source_entity": entity_id,
                "discipline": "mep" if "POINT" in str(symbol_map) else "architecture",
                "unit": "set" if "POINT" in str(symbol_map) else "m2",
            }
        )
    if not mapped:
        warnings.append({"code": "empty_entity_set", "message": "No entities supplied for normalization."})
    return _ok({"ok": True, "elements": mapped, "warnings": warnings})


def logic_compute(payload: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    defaults = payload.get("defaults", {})
    elements = payload.get("elements", [])
    warnings = []
    computed = []
    default_height = defaults.get("default_height_m", 3.0)
    for idx, element in enumerate(elements, start=1):
        if isinstance(element, dict):
            category = element.get("category", "generic")
            quantity = element.get("qty", element.get("quantity", 1))
        else:
            category = "generic"
            quantity = 1
        computed.append(
            {
                "id": f"CMP-{idx:03d}",
                "source_id": element.get("id", f"ELEM-{idx:03d}") if isinstance(element, dict) else str(element),
                "category": category,
                "qty": quantity,
                "unit": element.get("unit", "set") if isinstance(element, dict) else "set",
            }
        )
        if category in {"wall", "wall_finish"} and "height_m" not in (element or {}) if isinstance(element, dict) else True:
            warnings.append(
                {
                    "code": "missing_height_section_data",
                    "message": f"Used project default height {default_height} m.",
                    "fallback": "manual override for structural volume inputs",
                }
            )
    return _ok({"ok": True, "computed": computed, "warnings": warnings})


def boq_generate(payload: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    computed = payload.get("computed", [])
    direct_cost = float(len(computed) * 50000)
    factor_f = 1.272 if payload.get("factor_f", {}).get("mode") == "auto" else 1.0
    vat_enabled = payload.get("vat", {}).get("enabled", True)
    vat_multiplier = 1.07 if vat_enabled else 1.0
    return _ok(
        {
            "ok": True,
            "format": "po_workbook_bundle_v1",
            "po4_rows": len(computed),
            "po5_rows": max(1, min(18, len(computed))),
            "po6_total": round(direct_cost * factor_f * vat_multiplier, 2),
            "direct_cost": direct_cost,
            "factor_f": factor_f,
            "factor_f_applied": factor_f,
            "vat_enabled": vat_enabled,
            "template": build_workbook_template(),
            "reconciliation_status": "ready",
        }
    )


def export_xlsx(payload: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    if payload.get("conflicts_acknowledged") is False:
        return _error(
            409,
            "conflicting_quantities",
            "Cross-discipline conflicts must be resolved or explicitly acknowledged before export.",
            [{"action": "resolve_conflicts"}, {"action": "acknowledge_and_retry"}],
        )
    job_id = payload.get("job_id", "job_unknown")
    computed = list(payload.get("computed") or [])
    boq = dict(payload.get("boq") or {})
    workbook_template = dict(payload.get("workbook_template") or build_workbook_template())
    xlsx_path, json_path = write_export_bundle(
        job_id=job_id,
        computed=computed,
        boq=boq,
        workbook_template=workbook_template,
        output_dir=payload.get("output_dir"),
    )
    return _ok(
        {
            "ok": True,
            "xlsx": xlsx_path,
            "json": json_path,
            "xlsx_url": output_url(xlsx_path),
            "json_url": output_url(json_path),
            "workbook_template": workbook_template,
        }
    )


def acceptance_evaluate(payload: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    parity_gate_pct = float(payload.get("parity_gate_pct", 2.0))
    runtime_gate_min = float(payload.get("runtime_gate_minutes", 8.0))
    criteria = {
        "reconciliation_passed": bool(payload.get("reconciliation_passed")),
        "symbol_confidence_gte_095": float(payload.get("symbol_confidence", 0.0)) >= 0.95,
        "pdf_dwg_parity_lt_2pct": float(payload.get("parity_delta_pct", 100.0)) < parity_gate_pct,
        "audit_links_resolve": bool(payload.get("audit_links_resolve")),
        "performance_under_8_min": float(payload.get("runtime_minutes", 999.0)) < runtime_gate_min,
    }
    return _ok({"ok": all(criteria.values()), "criteria": criteria})


def optimize_plan(payload: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    request = TakeoffRequest.from_dict(payload)
    review_required = any(source.format == "pdf" and (request.config.pdf_scale_ratio is None or source.vector_pdf is False) for source in request.sources)
    plan = build_optimization_plan(request, review_required=review_required)
    return _ok({"ok": True, "job_id": request.job_id, "optimization": plan})
