from __future__ import annotations

from typing import Any

from .errors import QSJobError
from .report_generate_v2 import _normalize_po


def _warning(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def _normalize_report_payload(report_payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(report_payload, dict):
        raise QSJobError("invalid_handoff_review_input:report_not_object")
    if not str(report_payload.get("report_schema_version") or "").strip():
        raise QSJobError("invalid_handoff_review_input:report_schema_version_required")
    summary = report_payload.get("summary")
    if not isinstance(summary, dict):
        raise QSJobError("invalid_handoff_review_input:report_summary_not_object")
    sections = report_payload.get("sections")
    if not isinstance(sections, list):
        raise QSJobError("invalid_handoff_review_input:report_sections_not_list")
    return report_payload


def _normalize_consistency_payload(consistency_payload: dict[str, Any] | None) -> tuple[str, list[dict[str, str]]]:
    if consistency_payload is None:
        return "warning", [_warning("missing_consistency_details", "Consistency details are missing from handoff review inputs")]
    if not isinstance(consistency_payload, dict):
        raise QSJobError("invalid_handoff_review_input:consistency_not_object")
    if str(consistency_payload.get("consistency_schema_version") or "").strip() != "qs.consistency_check.v2":
        raise QSJobError("invalid_handoff_review_input:consistency_schema_version_invalid")
    status = str(consistency_payload.get("status") or "").strip()
    if status not in {"ok", "warning", "failed"}:
        raise QSJobError("invalid_handoff_review_input:consistency_status_invalid")
    return status, []


def _normalize_release_pack_payload(release_pack_payload: dict[str, Any] | None) -> tuple[bool, list[dict[str, str]]]:
    if release_pack_payload is None:
        return False, [_warning("missing_release_pack_details", "Release pack details are missing from handoff review inputs")]
    if not isinstance(release_pack_payload, dict):
        raise QSJobError("invalid_handoff_review_input:release_pack_not_object")
    if str(release_pack_payload.get("release_pack_schema_version") or "").strip() != "qs.release_pack.v2":
        raise QSJobError("invalid_handoff_review_input:release_pack_schema_version_invalid")
    approval_signals = release_pack_payload.get("approval_signals")
    if not isinstance(approval_signals, dict):
        raise QSJobError("invalid_handoff_review_input:release_pack_approval_signals_not_object")
    return bool(approval_signals.get("requires_po_review")), []


def _normalize_bundle_manifest_payload(bundle_manifest_payload: dict[str, Any] | None) -> tuple[bool, list[dict[str, str]]]:
    if bundle_manifest_payload is None:
        return False, [_warning("missing_bundle_manifest_details", "Bundle manifest details are missing from handoff review inputs")]
    if not isinstance(bundle_manifest_payload, dict):
        raise QSJobError("invalid_handoff_review_input:bundle_manifest_not_object")
    if str(bundle_manifest_payload.get("bundle_manifest_schema_version") or "").strip() != "qs.bundle_manifest.v2":
        raise QSJobError("invalid_handoff_review_input:bundle_manifest_schema_version_invalid")
    components = bundle_manifest_payload.get("components")
    review_checklist = bundle_manifest_payload.get("review_checklist")
    if not isinstance(components, dict):
        raise QSJobError("invalid_handoff_review_input:bundle_manifest_components_not_object")
    if not isinstance(review_checklist, list):
        raise QSJobError("invalid_handoff_review_input:bundle_manifest_review_checklist_not_list")
    all_present = bool(components.get("report")) and bool(components.get("release_pack"))
    return all_present, []


def _normalize_export_profile_payload(export_profile_payload: dict[str, Any] | None) -> tuple[bool, list[dict[str, str]]]:
    if export_profile_payload is None:
        return False, [_warning("missing_export_profile_details", "Export profile details are missing from handoff review inputs")]
    if not isinstance(export_profile_payload, dict):
        raise QSJobError("invalid_handoff_review_input:export_profile_not_object")
    if str(export_profile_payload.get("export_profile_schema_version") or "").strip() != "qs.export_profile.v2":
        raise QSJobError("invalid_handoff_review_input:export_profile_schema_version_invalid")
    deliverables = export_profile_payload.get("deliverables")
    handoff_summary = export_profile_payload.get("handoff_summary")
    if not isinstance(deliverables, list):
        raise QSJobError("invalid_handoff_review_input:export_profile_deliverables_not_list")
    if not isinstance(handoff_summary, dict):
        raise QSJobError("invalid_handoff_review_input:export_profile_handoff_summary_not_object")
    return True, []


def _normalize_po_payload(po_payload: dict[str, Any] | None) -> float | None:
    if po_payload is None:
        return None
    if not isinstance(po_payload, dict):
        raise QSJobError("invalid_handoff_review_input:po_not_object")
    po_total_cost, _ = _normalize_po(po_payload)
    return po_total_cost


def build_handoff_review_v2(
    report_payload: dict[str, Any],
    consistency_payload: dict[str, Any] | None = None,
    release_pack_payload: dict[str, Any] | None = None,
    bundle_manifest_payload: dict[str, Any] | None = None,
    export_profile_payload: dict[str, Any] | None = None,
    po_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    report_payload = _normalize_report_payload(report_payload)
    consistency_status, consistency_warnings = _normalize_consistency_payload(consistency_payload)
    requires_po_review, release_pack_warnings = _normalize_release_pack_payload(release_pack_payload)
    bundle_ready, bundle_warnings = _normalize_bundle_manifest_payload(bundle_manifest_payload)
    export_ready, export_warnings = _normalize_export_profile_payload(export_profile_payload)
    po_total_cost = _normalize_po_payload(po_payload)

    report_summary = report_payload["summary"]
    estimate_total_cost = None
    estimate_total_cost_raw = report_summary.get("estimate_total_cost")
    if estimate_total_cost_raw is not None:
        try:
            estimate_total_cost = round(float(estimate_total_cost_raw), 2)
        except (TypeError, ValueError) as exc:
            raise QSJobError("invalid_handoff_review_input:estimate_total_cost_invalid") from exc
    currency_raw = report_summary.get("currency")
    currency = str(currency_raw).strip() if currency_raw is not None and str(currency_raw).strip() else None

    warnings = sorted(
        consistency_warnings + release_pack_warnings + bundle_warnings + export_warnings,
        key=lambda item: (item["code"], item["message"]),
    )
    status = "warning" if warnings or consistency_status != "ok" else "ready"

    headline: dict[str, Any] = {
        "consistency_status": consistency_status,
        "warning_count": len(warnings),
        "requires_po_review": requires_po_review,
    }
    if estimate_total_cost is not None:
        headline["estimate_total_cost"] = estimate_total_cost
    if po_total_cost is not None:
        headline["po_total_cost"] = po_total_cost
    if currency is not None:
        headline["currency"] = currency

    decision_signals = [
        {
            "signal_id": "consistency_status",
            "level": consistency_status,
            "message": f"Consistency status is {consistency_status}.",
        },
        {
            "signal_id": "po_review",
            "level": "warning" if requires_po_review else "ok",
            "message": "PO review is required." if requires_po_review else "PO review is not required.",
        },
        {
            "signal_id": "bundle_readiness",
            "level": "ok" if bundle_ready and export_ready else "warning",
            "message": "Bundle and export profile are ready." if bundle_ready and export_ready else "Bundle or export profile needs review.",
        },
    ]

    operator_checks = [
        {"check_id": "report_ready", "status": "ok"},
        {"check_id": "consistency_reviewed", "status": "ok" if consistency_status == "ok" else "warning"},
        {"check_id": "export_profile_ready", "status": "ok" if export_ready else "warning"},
    ]

    return {
        "handoff_review_schema_version": "qs.handoff_review.v2",
        "review_kind": "qs.approval_prep_summary",
        "status": status,
        "headline": headline,
        "decision_signals": decision_signals,
        "operator_checks": operator_checks,
        "warnings": warnings,
    }
