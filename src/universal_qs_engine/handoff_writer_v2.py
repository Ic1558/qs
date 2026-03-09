from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .errors import QSJobError


def _warning(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def _validate_report_payload(report_payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(report_payload, dict):
        raise QSJobError("invalid_handoff_writer_input:report_not_object")
    if not str(report_payload.get("report_schema_version") or "").strip():
        raise QSJobError("invalid_handoff_writer_input:report_schema_version_required")
    summary = report_payload.get("summary")
    sections = report_payload.get("sections")
    if not isinstance(summary, dict):
        raise QSJobError("invalid_handoff_writer_input:report_summary_not_object")
    if not isinstance(sections, list):
        raise QSJobError("invalid_handoff_writer_input:report_sections_not_list")
    return report_payload


def _validate_handoff_review_payload(handoff_review_payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(handoff_review_payload, dict):
        raise QSJobError("invalid_handoff_writer_input:handoff_review_not_object")
    if str(handoff_review_payload.get("handoff_review_schema_version") or "").strip() != "qs.handoff_review.v2":
        raise QSJobError("invalid_handoff_writer_input:handoff_review_schema_version_invalid")
    if not isinstance(handoff_review_payload.get("headline"), dict):
        raise QSJobError("invalid_handoff_writer_input:handoff_review_headline_not_object")
    if not isinstance(handoff_review_payload.get("decision_signals"), list):
        raise QSJobError("invalid_handoff_writer_input:handoff_review_decision_signals_not_list")
    if not isinstance(handoff_review_payload.get("operator_checks"), list):
        raise QSJobError("invalid_handoff_writer_input:handoff_review_operator_checks_not_list")
    return handoff_review_payload


def _validate_optional_payload(payload: dict[str, Any] | None, *, schema_key: str, schema_value: str, error_prefix: str) -> bool:
    if payload is None:
        return False
    if not isinstance(payload, dict):
        raise QSJobError(f"{error_prefix}:payload_not_object")
    if str(payload.get(schema_key) or "").strip() != schema_value:
        raise QSJobError(f"{error_prefix}:schema_invalid")
    return True


def _write_atomic_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


def _write_atomic_json(path: Path, payload: dict[str, Any]) -> None:
    _write_atomic_text(path, json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n")


def _render_approval_summary_md(
    *,
    report_payload: dict[str, Any],
    handoff_review_payload: dict[str, Any],
    export_profile_payload: dict[str, Any] | None,
    release_pack_payload: dict[str, Any] | None,
    warnings: list[dict[str, str]],
) -> str:
    report_summary = report_payload["summary"]
    headline = handoff_review_payload["headline"]
    decision_signals = handoff_review_payload["decision_signals"]
    operator_checks = handoff_review_payload["operator_checks"]
    deliverables = export_profile_payload.get("deliverables", []) if isinstance(export_profile_payload, dict) else []

    lines = [
        "# QS Approval Summary",
        "",
        "## Headline",
        f"- Report profile: {str(report_payload.get('report_profile_id') or '')}",
        f"- Consistency status: {str(headline.get('consistency_status') or '')}",
    ]
    if "estimate_total_cost" in report_summary:
        lines.append(f"- Estimate total cost: {report_summary['estimate_total_cost']}")
    if "po_total_cost" in headline:
        lines.append(f"- PO total cost: {headline['po_total_cost']}")
    if "currency" in headline:
        lines.append(f"- Currency: {headline['currency']}")

    lines.extend(["", "## Decision Signals"])
    for signal in decision_signals:
        lines.append(f"- {signal['signal_id']}: {signal['level']} - {signal['message']}")

    lines.extend(["", "## Operator Checks"])
    for check in operator_checks:
        lines.append(f"- {check['check_id']}: {check['status']}")

    lines.extend(["", "## Deliverables"])
    for item in deliverables:
        lines.append(
            f"- {item['deliverable_id']}: artifact={item['artifact_type']} required={str(item['required']).lower()} present={str(item['present']).lower()}"
        )
    if not deliverables and isinstance(release_pack_payload, dict):
        lines.append("- approval_pack: present in nested payload stack")

    lines.extend(["", "## Warnings"])
    if warnings:
        for warning in warnings:
            lines.append(f"- {warning['code']}: {warning['message']}")
    else:
        lines.append("- none")

    return "\n".join(lines) + "\n"


def write_handoff_artifacts_v2(
    output_dir: str | Path,
    *,
    report_payload: dict[str, Any],
    handoff_review_payload: dict[str, Any],
    export_profile_payload: dict[str, Any] | None = None,
    release_pack_payload: dict[str, Any] | None = None,
    bundle_manifest_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    report_payload = _validate_report_payload(report_payload)
    handoff_review_payload = _validate_handoff_review_payload(handoff_review_payload)
    has_export = _validate_optional_payload(
        export_profile_payload,
        schema_key="export_profile_schema_version",
        schema_value="qs.export_profile.v2",
        error_prefix="invalid_handoff_writer_input:export_profile",
    )
    has_release_pack = _validate_optional_payload(
        release_pack_payload,
        schema_key="release_pack_schema_version",
        schema_value="qs.release_pack.v2",
        error_prefix="invalid_handoff_writer_input:release_pack",
    )
    has_bundle_manifest = _validate_optional_payload(
        bundle_manifest_payload,
        schema_key="bundle_manifest_schema_version",
        schema_value="qs.bundle_manifest.v2",
        error_prefix="invalid_handoff_writer_input:bundle_manifest",
    )

    out_dir = Path(output_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    warnings: list[dict[str, str]] = []
    if not has_export:
        warnings.append(_warning("missing_export_profile_details", "Export profile details were not provided for handoff writing"))
    if not has_release_pack:
        warnings.append(_warning("missing_release_pack_details", "Release pack details were not provided for handoff writing"))
    if not has_bundle_manifest:
        warnings.append(_warning("missing_bundle_manifest_details", "Bundle manifest details were not provided for handoff writing"))
    warnings = sorted(warnings, key=lambda item: (item["code"], item["message"]))

    written_files: list[dict[str, str]] = []

    handoff_review_path = out_dir / "handoff_review.json"
    _write_atomic_json(handoff_review_path, handoff_review_payload)
    written_files.append({"artifact_type": "handoff_review", "path": str(handoff_review_path)})

    if has_export and export_profile_payload is not None:
        export_profile_path = out_dir / "export_profile.json"
        _write_atomic_json(export_profile_path, export_profile_payload)
        written_files.append({"artifact_type": "export_profile", "path": str(export_profile_path)})

    if has_bundle_manifest and bundle_manifest_payload is not None:
        bundle_manifest_path = out_dir / "bundle_manifest.json"
        _write_atomic_json(bundle_manifest_path, bundle_manifest_payload)
        written_files.append({"artifact_type": "bundle_manifest", "path": str(bundle_manifest_path)})

    approval_summary_path = out_dir / "approval_summary.md"
    _write_atomic_text(
        approval_summary_path,
        _render_approval_summary_md(
            report_payload=report_payload,
            handoff_review_payload=handoff_review_payload,
            export_profile_payload=export_profile_payload,
            release_pack_payload=release_pack_payload,
            warnings=warnings,
        ),
    )
    written_files.append({"artifact_type": "approval_summary", "path": str(approval_summary_path)})

    return {
        "handoff_writer_schema_version": "qs.handoff_writer.v2",
        "status": "warning" if warnings else "written",
        "written_files": written_files,
        "warnings": warnings,
    }
