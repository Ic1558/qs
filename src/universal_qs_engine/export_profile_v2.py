from __future__ import annotations

from typing import Any

from .errors import QSJobError
from .report_generate_v2 import _normalize_po


def _warning(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def _normalize_report_payload(report_payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(report_payload, dict):
        raise QSJobError("invalid_export_profile_input:report_not_object")
    if not str(report_payload.get("report_schema_version") or "").strip():
        raise QSJobError("invalid_export_profile_input:report_schema_version_required")
    summary = report_payload.get("summary")
    if not isinstance(summary, dict):
        raise QSJobError("invalid_export_profile_input:report_summary_not_object")
    sections = report_payload.get("sections")
    if not isinstance(sections, list):
        raise QSJobError("invalid_export_profile_input:report_sections_not_list")
    return report_payload


def _normalize_consistency_payload(consistency_payload: dict[str, Any] | None) -> tuple[str, list[dict[str, str]]]:
    if consistency_payload is None:
        return "warning", [_warning("missing_consistency_details", "Consistency details are missing from export inputs")]
    if not isinstance(consistency_payload, dict):
        raise QSJobError("invalid_export_profile_input:consistency_not_object")
    if str(consistency_payload.get("consistency_schema_version") or "").strip() != "qs.consistency_check.v2":
        raise QSJobError("invalid_export_profile_input:consistency_schema_version_invalid")
    status = str(consistency_payload.get("status") or "").strip()
    if status not in {"ok", "warning", "failed"}:
        raise QSJobError("invalid_export_profile_input:consistency_status_invalid")
    return status, []


def _normalize_release_pack_payload(release_pack_payload: dict[str, Any] | None) -> tuple[dict[str, Any] | None, list[dict[str, str]]]:
    if release_pack_payload is None:
        return None, [_warning("missing_release_pack_details", "Release pack details are missing from export inputs")]
    if not isinstance(release_pack_payload, dict):
        raise QSJobError("invalid_export_profile_input:release_pack_not_object")
    if str(release_pack_payload.get("release_pack_schema_version") or "").strip() != "qs.release_pack.v2":
        raise QSJobError("invalid_export_profile_input:release_pack_schema_version_invalid")
    approval_signals = release_pack_payload.get("approval_signals")
    if not isinstance(approval_signals, dict):
        raise QSJobError("invalid_export_profile_input:release_pack_approval_signals_not_object")
    return release_pack_payload, []


def _normalize_bundle_manifest_payload(bundle_manifest_payload: dict[str, Any] | None) -> tuple[dict[str, Any] | None, list[dict[str, str]]]:
    if bundle_manifest_payload is None:
        return None, [_warning("missing_bundle_manifest_details", "Bundle manifest details are missing from export inputs")]
    if not isinstance(bundle_manifest_payload, dict):
        raise QSJobError("invalid_export_profile_input:bundle_manifest_not_object")
    if str(bundle_manifest_payload.get("bundle_manifest_schema_version") or "").strip() != "qs.bundle_manifest.v2":
        raise QSJobError("invalid_export_profile_input:bundle_manifest_schema_version_invalid")
    components = bundle_manifest_payload.get("components")
    review_checklist = bundle_manifest_payload.get("review_checklist")
    if not isinstance(components, dict):
        raise QSJobError("invalid_export_profile_input:bundle_manifest_components_not_object")
    if not isinstance(review_checklist, list):
        raise QSJobError("invalid_export_profile_input:bundle_manifest_review_checklist_not_list")
    return bundle_manifest_payload, []


def _normalize_po_payload(po_payload: dict[str, Any] | None) -> tuple[float | None, bool]:
    if po_payload is None:
        return None, False
    if not isinstance(po_payload, dict):
        raise QSJobError("invalid_export_profile_input:po_not_object")
    po_total_cost, _ = _normalize_po(po_payload)
    return po_total_cost, True


def build_export_profile_v2(
    report_payload: dict[str, Any],
    consistency_payload: dict[str, Any] | None = None,
    release_pack_payload: dict[str, Any] | None = None,
    bundle_manifest_payload: dict[str, Any] | None = None,
    po_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    report_payload = _normalize_report_payload(report_payload)
    consistency_status, consistency_warnings = _normalize_consistency_payload(consistency_payload)
    release_pack_payload, release_pack_warnings = _normalize_release_pack_payload(release_pack_payload)
    bundle_manifest_payload, bundle_manifest_warnings = _normalize_bundle_manifest_payload(bundle_manifest_payload)
    po_total_cost, has_po = _normalize_po_payload(po_payload)

    report_summary = report_payload["summary"]
    estimate_total_cost_raw = report_summary.get("estimate_total_cost")
    estimate_total_cost = None
    if estimate_total_cost_raw is not None:
        try:
            estimate_total_cost = round(float(estimate_total_cost_raw), 2)
        except (TypeError, ValueError) as exc:
            raise QSJobError("invalid_export_profile_input:estimate_total_cost_invalid") from exc

    currency_raw = report_summary.get("currency")
    currency = str(currency_raw).strip() if currency_raw is not None and str(currency_raw).strip() else None

    warnings = sorted(
        consistency_warnings + release_pack_warnings + bundle_manifest_warnings,
        key=lambda item: (item["code"], item["message"]),
    )
    status = "warning" if warnings or consistency_status != "ok" else "ready"

    deliverables = [
        {
            "deliverable_id": "report",
            "artifact_type": "project_qs_report",
            "required": True,
            "present": True,
        },
        {
            "deliverable_id": "po",
            "artifact_type": "po_document",
            "required": False,
            "present": has_po,
        },
    ]

    review_targets = [
        {"target_id": "cost_summary", "source": "report"},
        {"target_id": "consistency_review", "source": "consistency_check"},
        {"target_id": "approval_pack", "source": "release_pack"},
    ]

    handoff_summary: dict[str, Any] = {
        "report_profile_id": str(report_payload.get("report_profile_id") or ""),
        "consistency_status": consistency_status,
        "warning_count": len(warnings),
    }
    if estimate_total_cost is not None:
        handoff_summary["estimate_total_cost"] = estimate_total_cost
    if po_total_cost is not None:
        handoff_summary["po_total_cost"] = po_total_cost
    if currency is not None:
        handoff_summary["currency"] = currency

    return {
        "export_profile_schema_version": "qs.export_profile.v2",
        "export_kind": "qs.operator_handoff",
        "status": status,
        "deliverables": deliverables,
        "handoff_summary": handoff_summary,
        "review_targets": review_targets,
        "warnings": warnings,
    }
