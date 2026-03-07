from __future__ import annotations

from typing import Dict, List

from .contracts import (
    AuditLink,
    ElementRecord,
    PreviewResult,
    ProjectConfig,
    ReviewItem,
    TakeoffRequest,
    WorkbookPlan,
)
from .optimizer import build_optimization_plan
from .workbook import build_workbook_template, workbook_tabs


SUPPORTED_FORMATS = ["pdf", "dwg", "dxf"]
WORKBOOK_TABS = workbook_tabs()


def _build_stages(request: TakeoffRequest) -> List[Dict[str, str]]:
    disciplines = {source.discipline for source in request.sources}
    stages = [
        {"name": "intake", "status": "ready"},
        {"name": "normalization", "status": "ready"},
    ]
    for discipline in ("architecture", "structure", "mep"):
        stages.append(
            {
                "name": f"{discipline}_logic",
                "status": "ready" if discipline in disciplines else "skipped",
            }
        )
    stages.extend(
        [
            {"name": "boq_mapping", "status": "ready"},
            {"name": "audit_export", "status": "ready"},
        ]
    )
    return stages


def _sample_element_for(source, config: ProjectConfig) -> ElementRecord:
    floor_to_floor_height_m = config.floor_to_floor_height_m
    if source.discipline == "architecture":
        proof = {"length_m": 8.0, "height_m": 3.0, "opening_area_m2": 1.8}
        quantity = proof["length_m"] * proof["height_m"] - proof["opening_area_m2"]
        return ElementRecord(
            id="arch-wall-001",
            discipline="architecture",
            category="wall_finish",
            unit="m2",
            quantity=round(quantity, 3),
            formula="(length_m * height_m) - opening_area_m2",
            proof=proof,
            audit_link=AuditLink(source.path, source.discipline, "page:1@x=120,y=240"),
            confidence=0.98 if source.vector_pdf is not False else 0.9,
            sub_items=[{"type": "trim", "quantity": 1, "unit": "lot"}],
        )
    if source.discipline == "structure":
        proof = {"sectional_area_m2": 0.12, "length_m": 6.5, "rebar_density_kg_m3": 110.0}
        volume = proof["sectional_area_m2"] * proof["length_m"]
        return ElementRecord(
            id="str-beam-001",
            discipline="structure",
            category="reinforced_concrete_beam",
            unit="m3",
            quantity=round(volume, 3),
            formula="sectional_area_m2 * length_m",
            proof=proof,
            audit_link=AuditLink(source.path, source.discipline, "entity:BEAM-17"),
            confidence=0.99,
            sub_items=[
                {
                    "type": "rebar_estimate",
                    "quantity": round(volume * proof["rebar_density_kg_m3"], 3),
                    "unit": "kg",
                }
            ],
        )
    proof = {
        "path_length_m": 14.0,
        "turn_count": 3,
        "riser_count": 2,
        "floor_to_floor_height_m": floor_to_floor_height_m,
        "riser_mode": config.riser_mode,
        "manual_riser_count": config.manual_riser_count,
    }
    if config.riser_mode == "manual":
        riser_count = max(0, config.manual_riser_count)
        quantity = proof["path_length_m"] + (riser_count * floor_to_floor_height_m)
        formula = "path_length_m + (manual_riser_count * floor_to_floor_height_m)" if riser_count else "path_length_m"
    else:
        riser_count = proof["riser_count"]
        quantity = proof["path_length_m"] + (riser_count * floor_to_floor_height_m)
        formula = "path_length_m + (riser_count * floor_to_floor_height_m)"
    return ElementRecord(
        id="mep-run-001",
        discipline="mep",
        category="conduit_run",
        unit="m",
        quantity=round(quantity, 3),
        formula=formula,
        proof=proof,
        audit_link=AuditLink(source.path, source.discipline, "page:2@x=310,y=182"),
        confidence=0.96,
        sub_items=[{"type": "elbow_90", "quantity": proof["turn_count"], "unit": "ea"}],
    )


def _build_review_queue(request: TakeoffRequest) -> List[ReviewItem]:
    queue: List[ReviewItem] = []
    for source in request.sources:
        if source.format == "pdf" and request.config.pdf_scale_ratio is None:
            queue.append(
                ReviewItem(
                    code="pdf_scale_required",
                    severity="high",
                    message="PDF scale calibration is required before final quantity extraction.",
                    source_file=source.path,
                )
            )
        if source.format == "pdf" and source.vector_pdf is False:
            queue.append(
                ReviewItem(
                    code="ocr_confidence_review",
                    severity="medium",
                    message="Scanned PDF intake should be reviewed if OCR or symbol confidence falls below 0.95.",
                    source_file=source.path,
                )
            )
    return queue


def build_preview_result(request: TakeoffRequest) -> PreviewResult:
    elements = [_sample_element_for(source, request.config) for source in request.sources]
    review_queue = _build_review_queue(request)
    status = "review_required" if review_queue else "ready"
    workbook = WorkbookPlan(
        filename=f"{request.job_id}_po4_po5_po6.xlsx",
        tabs=WORKBOOK_TABS,
        notes=[
            "PO-4 includes formula proofs and source locators.",
            "PO-5 aggregates pricing and waste factors by category.",
            "PO-6 summarizes totals with Factor F and VAT options.",
        ],
        template=build_workbook_template(),
    )
    fallback_rules = [
        {
            "code": "missing_scale",
            "when": "pdf_scale_ratio is null for a PDF source",
            "behavior": "block extraction and request manual scale entry",
        },
        {
            "code": "low_symbol_confidence",
            "when": "symbol confidence < 0.95",
            "behavior": "route to Manual Review and allow re-map",
        },
        {
            "code": "unknown_layer_block",
            "when": "layer or block is not mapped",
            "behavior": "assign Unclassified bucket and store mapping template after review",
        },
        {
            "code": "conflicting_quantities",
            "when": "cross-discipline totals mismatch",
            "behavior": "block export until resolved or acknowledged",
        },
    ]
    acceptance_gate = {
        "final_gate": [
            "PO-4/PO-5/PO-6 export reconciles",
            "symbol recognition confidence >= 0.95",
            f"PDF vs DWG parity < {request.config.parity_gate_pct}%",
            "audit links resolve",
            f"runtime under {request.config.runtime_cap_minutes} minutes",
        ]
    }
    optimization_plan = build_optimization_plan(request, review_required=bool(review_queue))
    integration = {
        "module_label": "com.0luka.universal-qs-api",
        "health_url": "http://127.0.0.1:7084/api/health",
        "preview_url": "http://127.0.0.1:7084/api/v1/takeoff/preview",
        "api_contracts": [
            "/api/v1/intake/prepare",
            "/api/v1/extract/dwg",
            "/api/v1/extract/pdf",
            "/api/v1/map/schema",
            "/api/v1/logic/compute",
            "/api/v1/boq/generate",
            "/api/v1/export/xlsx",
            "/api/v1/acceptance/evaluate",
            "/api/v1/optimize/plan",
        ],
        "trace_fields": ["trace_id", "job_id", "source_file", "discipline"],
        "factor_f_table": request.config.factor_f_table,
        "cost_guardrails": {
            "ocr_page_cap_pct": request.config.ocr_page_cap_pct,
            "vision_page_cap_pct": request.config.vision_page_cap_pct,
            "storage_cap_mb": request.config.storage_cap_mb,
            "runtime_cap_minutes": request.config.runtime_cap_minutes,
            "parity_gate_pct": request.config.parity_gate_pct,
        },
        "execution_controls": {
            "vision_enabled": request.config.vision_enabled,
            "vision_requires_approval": request.config.vision_requires_approval,
            "riser_mode": request.config.riser_mode,
            "cache_policy": request.config.cache_policy,
            "delta_execution_enabled": request.config.delta_execution_enabled,
        },
    }
    return PreviewResult(
        schema_version="universal_qs_result_v1",
        job_id=request.job_id,
        project_name=request.config.project_name,
        status=status,
        supported_formats=SUPPORTED_FORMATS,
        stages=_build_stages(request),
        elements=elements,
        review_queue=review_queue,
        workbook=workbook,
        fallback_rules=fallback_rules,
        acceptance_gate=acceptance_gate,
        optimization_plan=optimization_plan,
        integration=integration,
    )
