from __future__ import annotations

from typing import Any

from .errors import QSJobError
from .report_generate_v2 import _normalize_po


def _warning(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def _normalize_report_payload(report_payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(report_payload, dict):
        raise QSJobError("invalid_bundle_manifest_input:report_not_object")
    if not str(report_payload.get("report_schema_version") or "").strip():
        raise QSJobError("invalid_bundle_manifest_input:report_schema_version_required")
    summary = report_payload.get("summary")
    if not isinstance(summary, dict):
        raise QSJobError("invalid_bundle_manifest_input:report_summary_not_object")
    sections = report_payload.get("sections")
    if not isinstance(sections, list):
        raise QSJobError("invalid_bundle_manifest_input:report_sections_not_list")
    if not str(report_payload.get("report_profile_id") or "").strip():
        raise QSJobError("invalid_bundle_manifest_input:report_profile_id_required")
    return report_payload


def _normalize_consistency_payload(consistency_payload: dict[str, Any] | None) -> tuple[str, list[dict[str, str]], bool]:
    if consistency_payload is None:
        return (
            "warning",
            [_warning("missing_consistency_details", "Consistency details are missing from bundle inputs")],
            False,
        )

    if not isinstance(consistency_payload, dict):
        raise QSJobError("invalid_bundle_manifest_input:consistency_not_object")
    if str(consistency_payload.get("consistency_schema_version") or "").strip() != "qs.consistency_check.v2":
        raise QSJobError("invalid_bundle_manifest_input:consistency_schema_version_invalid")
    status = str(consistency_payload.get("status") or "").strip()
    if status not in {"ok", "warning", "failed"}:
        raise QSJobError("invalid_bundle_manifest_input:consistency_status_invalid")
    checks = consistency_payload.get("checks")
    if not isinstance(checks, dict):
        raise QSJobError("invalid_bundle_manifest_input:consistency_checks_not_object")
    warnings = consistency_payload.get("warnings")
    if not isinstance(warnings, list):
        raise QSJobError("invalid_bundle_manifest_input:consistency_warnings_not_list")
    normalized: list[dict[str, str]] = []
    for index, item in enumerate(warnings):
        if not isinstance(item, dict):
            raise QSJobError(f"invalid_bundle_manifest_input:consistency_warning_not_object:{index}")
        code = str(item.get("code") or "").strip()
        message = str(item.get("message") or "").strip()
        if not code or not message:
            raise QSJobError(f"invalid_bundle_manifest_input:consistency_warning_fields_required:{index}")
        normalized.append({"code": code, "message": message})
    return status, sorted(normalized, key=lambda item: (item["code"], item["message"])), True


def _normalize_release_pack_payload(release_pack_payload: dict[str, Any] | None) -> tuple[dict[str, Any] | None, list[dict[str, str]], bool]:
    if release_pack_payload is None:
        return None, [_warning("missing_release_pack_details", "Release pack details are missing from bundle inputs")], False
    if not isinstance(release_pack_payload, dict):
        raise QSJobError("invalid_bundle_manifest_input:release_pack_not_object")
    if str(release_pack_payload.get("release_pack_schema_version") or "").strip() != "qs.release_pack.v2":
        raise QSJobError("invalid_bundle_manifest_input:release_pack_schema_version_invalid")
    if str(release_pack_payload.get("release_kind") or "").strip() != "qs.approval_review_pack":
        raise QSJobError("invalid_bundle_manifest_input:release_kind_invalid")
    approval_signals = release_pack_payload.get("approval_signals")
    if not isinstance(approval_signals, dict):
        raise QSJobError("invalid_bundle_manifest_input:release_pack_approval_signals_not_object")
    sections = release_pack_payload.get("sections")
    if not isinstance(sections, list):
        raise QSJobError("invalid_bundle_manifest_input:release_pack_sections_not_list")
    warnings = release_pack_payload.get("warnings")
    if not isinstance(warnings, list):
        raise QSJobError("invalid_bundle_manifest_input:release_pack_warnings_not_list")
    normalized: list[dict[str, str]] = []
    for index, item in enumerate(warnings):
        if not isinstance(item, dict):
            raise QSJobError(f"invalid_bundle_manifest_input:release_pack_warning_not_object:{index}")
        code = str(item.get("code") or "").strip()
        message = str(item.get("message") or "").strip()
        if not code or not message:
            raise QSJobError(f"invalid_bundle_manifest_input:release_pack_warning_fields_required:{index}")
        normalized.append({"code": code, "message": message})
    return release_pack_payload, sorted(normalized, key=lambda item: (item["code"], item["message"])), True


def _normalize_po_payload(po_payload: dict[str, Any] | None) -> tuple[float | None, bool]:
    if po_payload is None:
        return None, False
    if not isinstance(po_payload, dict):
        raise QSJobError("invalid_bundle_manifest_input:po_not_object")
    po_total_cost, _ = _normalize_po(po_payload)
    return po_total_cost, True


def build_bundle_manifest_v2(
    report_payload: dict[str, Any],
    consistency_payload: dict[str, Any] | None = None,
    release_pack_payload: dict[str, Any] | None = None,
    po_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_report = _normalize_report_payload(report_payload)
    consistency_status, consistency_warnings, has_consistency = _normalize_consistency_payload(consistency_payload)
    normalized_release_pack, release_pack_warnings, has_release_pack = _normalize_release_pack_payload(release_pack_payload)
    po_total_cost, has_po = _normalize_po_payload(po_payload)

    report_summary = normalized_report["summary"]
    estimate_total_cost = report_summary.get("estimate_total_cost")
    if estimate_total_cost is not None:
        try:
            estimate_total_cost = round(float(estimate_total_cost), 2)
        except (TypeError, ValueError) as exc:
            raise QSJobError("invalid_bundle_manifest_input:estimate_total_cost_invalid") from exc

    currency_value = report_summary.get("currency")
    currency = str(currency_value).strip() if currency_value is not None and str(currency_value).strip() else None

    warnings = sorted(consistency_warnings + release_pack_warnings, key=lambda item: (item["code"], item["message"]))
    status = "warning" if warnings or consistency_status != "ok" else "ready"

    artifact_manifest = [
        {"artifact_type": "project_qs_report", "logical_role": "report"},
    ]
    if has_po:
        artifact_manifest.append({"artifact_type": "po_document", "logical_role": "po"})

    requires_po_review = False
    if normalized_release_pack is not None:
        approval_signals = normalized_release_pack["approval_signals"]
        requires_po_review = bool(approval_signals.get("requires_po_review"))

    review_checklist = [
        {"check_id": "report_present", "label": "Report present", "status": "ok"},
        {
            "check_id": "consistency_reviewed",
            "label": "Consistency reviewed",
            "status": "ok" if consistency_status == "ok" else "warning",
        },
        {
            "check_id": "po_review_required",
            "label": "PO review required",
            "status": "warning" if requires_po_review else "ok",
        },
    ]

    summary: dict[str, Any] = {
        "report_profile_id": str(normalized_report.get("report_profile_id") or ""),
        "consistency_status": consistency_status,
        "warning_count": len(warnings),
    }
    if estimate_total_cost is not None:
        summary["estimate_total_cost"] = estimate_total_cost
    if po_total_cost is not None:
        summary["po_total_cost"] = po_total_cost
    if currency is not None:
        summary["currency"] = currency

    return {
        "bundle_manifest_schema_version": "qs.bundle_manifest.v2",
        "bundle_kind": "qs.approval_ready_bundle",
        "status": status,
        "components": {
            "report": True,
            "consistency_check": has_consistency,
            "release_pack": has_release_pack,
            "po": has_po,
        },
        "summary": summary,
        "artifact_manifest": artifact_manifest,
        "review_checklist": review_checklist,
        "warnings": warnings,
    }
