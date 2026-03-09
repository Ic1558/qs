from __future__ import annotations

from typing import Any

from .errors import QSJobError
from .report_generate_v2 import _load_json_ref, _normalize_po


def _warning(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def _extract_report_payload(report_doc: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
    if "report_generate" in report_doc:
        report_payload = report_doc.get("report_generate")
        if not isinstance(report_payload, dict):
            raise QSJobError("invalid_release_pack_input:report_generate_not_object")
        consistency = report_doc.get("consistency_check")
        if consistency is not None and not isinstance(consistency, dict):
            raise QSJobError("invalid_release_pack_input:consistency_check_not_object")
        return report_payload, consistency if isinstance(consistency, dict) else None

    return report_doc, None


def _normalize_report_payload(report_doc: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
    report_payload, embedded_consistency = _extract_report_payload(report_doc)
    schema_version = str(report_payload.get("report_schema_version") or "").strip()
    if not schema_version:
        raise QSJobError("invalid_release_pack_input:report_schema_version_required")
    summary = report_payload.get("summary")
    if not isinstance(summary, dict):
        raise QSJobError("invalid_release_pack_input:report_summary_not_object")
    sections = report_payload.get("sections")
    if not isinstance(sections, list):
        raise QSJobError("invalid_release_pack_input:report_sections_not_list")
    if not str(report_payload.get("report_profile_id") or "").strip():
        raise QSJobError("invalid_release_pack_input:report_profile_id_required")
    return report_payload, embedded_consistency


def _normalize_consistency(consistency_doc: dict[str, Any] | None) -> tuple[str, list[dict[str, str]]]:
    if consistency_doc is None:
        return "warning", [_warning("missing_consistency_details", "Consistency details are missing from report input")]

    status = str(consistency_doc.get("status") or "").strip()
    if status not in {"ok", "warning", "failed"}:
        raise QSJobError("invalid_release_pack_input:consistency_status_invalid")
    warnings = consistency_doc.get("warnings")
    if not isinstance(warnings, list):
        raise QSJobError("invalid_release_pack_input:consistency_warnings_not_list")
    normalized: list[dict[str, str]] = []
    for index, item in enumerate(warnings):
        if not isinstance(item, dict):
            raise QSJobError(f"invalid_release_pack_input:consistency_warning_not_object:{index}")
        code = str(item.get("code") or "").strip()
        message = str(item.get("message") or "").strip()
        if not code or not message:
            raise QSJobError(f"invalid_release_pack_input:consistency_warning_fields_required:{index}")
        normalized.append({"code": code, "message": message})
    return status, sorted(normalized, key=lambda item: (item["code"], item["message"]))


def _build_release_pack_from_docs(report_doc: dict[str, Any], po_doc: dict[str, Any] | None, *, report_ref: str, po_ref: str | None) -> dict[str, Any]:
    report_payload, embedded_consistency = _normalize_report_payload(report_doc)
    report_summary = report_payload["summary"]

    report_profile_id = str(report_payload.get("report_profile_id") or "").strip()
    project_id = report_summary.get("project_id")
    project_value = str(project_id).strip() if project_id is not None and str(project_id).strip() else None

    estimate_total_raw = report_summary.get("estimate_total_cost")
    estimate_total_cost = None
    if estimate_total_raw is not None:
        try:
            estimate_total_cost = round(float(estimate_total_raw), 2)
        except (TypeError, ValueError) as exc:
            raise QSJobError("invalid_release_pack_input:estimate_total_cost_invalid") from exc

    currency_raw = report_summary.get("currency")
    currency = str(currency_raw).strip() if currency_raw is not None and str(currency_raw).strip() else None

    po_total_cost = None
    po_currency = None
    if po_doc is not None:
        po_total_cost, po_currency = _normalize_po(po_doc)

    consistency_status, consistency_warnings = _normalize_consistency(embedded_consistency)
    warnings = list(consistency_warnings)
    warnings = sorted(warnings, key=lambda item: (item["code"], item["message"]))

    status = "warning" if warnings or consistency_status != "ok" else "ready"
    section_order = [
        {"section_id": "executive_summary", "title": "Executive Summary"},
        {"section_id": "cost_summary", "title": "Cost Summary"},
        {"section_id": "po_summary", "title": "PO Summary"},
        {"section_id": "consistency_review", "title": "Consistency Review"},
    ]

    summary: dict[str, Any] = {"report_profile_id": report_profile_id}
    if project_value is not None:
        summary["project_id"] = project_value
    if estimate_total_cost is not None:
        summary["estimate_total_cost"] = estimate_total_cost
    if po_total_cost is not None:
        summary["po_total_cost"] = po_total_cost
    if currency is not None:
        summary["currency"] = currency
    elif po_currency is not None:
        summary["currency"] = po_currency

    source_snapshot: dict[str, Any] = {"report_ref": report_ref}
    if po_ref is not None:
        source_snapshot["po_ref"] = po_ref

    return {
        "release_pack_schema_version": "qs.release_pack.v2",
        "release_kind": "qs.approval_review_pack",
        "status": status,
        "summary": summary,
        "approval_signals": {
            "requires_po_review": po_doc is not None,
            "consistency_status": consistency_status,
            "warning_count": len(warnings),
        },
        "sections": section_order,
        "warnings": warnings,
        "source_snapshot": source_snapshot,
    }


def build_release_pack_from_payload(report_payload: dict[str, Any], consistency_payload: dict[str, Any] | None = None, po_payload: dict[str, Any] | None = None) -> dict[str, Any]:
    report_doc: dict[str, Any] = {"report_generate": report_payload}
    if consistency_payload is not None:
        report_doc["consistency_check"] = consistency_payload
    return _build_release_pack_from_docs(report_doc, po_payload, report_ref="inline:report_generate_v2", po_ref="inline:po_v2" if po_payload is not None else None)


def build_release_pack_v2(report_ref: str, po_ref: str | None = None) -> dict[str, Any]:
    report_doc = _load_json_ref(report_ref, ref_name="report_ref")
    po_doc = _load_json_ref(po_ref, ref_name="po_ref") if po_ref is not None else None
    return _build_release_pack_from_docs(
        report_doc,
        po_doc,
        report_ref=str(report_ref),
        po_ref=str(po_ref) if po_ref is not None else None,
    )
