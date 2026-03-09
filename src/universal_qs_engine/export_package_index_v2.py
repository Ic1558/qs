from __future__ import annotations

from pathlib import Path
from typing import Any

from .errors import QSJobError


def _warning(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def build_export_package_index_v2(
    output_dir: str | Path,
    written_files: list[dict[str, Any]],
    *,
    handoff_writer_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root = Path(output_dir).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise QSJobError("invalid_export_package_index_input:output_dir_missing")
    if not isinstance(written_files, list):
        raise QSJobError("invalid_export_package_index_input:written_files_not_list")

    allowed = {
        "handoff_review": ("handoff_review.json", True),
        "approval_summary": ("approval_summary.md", True),
        "export_profile": ("export_profile.json", False),
        "bundle_manifest": ("bundle_manifest.json", False),
    }
    observed_types: set[str] = set()
    for item in written_files:
        if not isinstance(item, dict):
            raise QSJobError("invalid_export_package_index_input:written_file_not_object")
        artifact_type = str(item.get("artifact_type") or "").strip()
        path_text = str(item.get("path") or "").strip()
        if artifact_type not in allowed:
            raise QSJobError("invalid_export_package_index_input:artifact_type_unknown")
        if not path_text:
            raise QSJobError("invalid_export_package_index_input:path_missing")
        path = Path(path_text).expanduser().resolve()
        if not path.is_relative_to(root):
            raise QSJobError("invalid_export_package_index_input:path_outside_output_dir")
        observed_types.add(artifact_type)

    warnings: list[dict[str, str]] = []
    items: list[dict[str, Any]] = []
    for artifact_type, (filename, required) in sorted(allowed.items(), key=lambda entry: entry[1][0]):
        present = (root / filename).exists()
        items.append(
            {
                "artifact_type": artifact_type,
                "filename": filename,
                "present": present,
            }
        )
        if required and not present:
            warnings.append(
                _warning(
                    "missing_required_file",
                    f"Required handoff artifact missing: {filename}",
                )
            )

    if handoff_writer_result is not None:
        if not isinstance(handoff_writer_result, dict):
            raise QSJobError("invalid_export_package_index_input:handoff_writer_result_not_object")
        if str(handoff_writer_result.get("handoff_writer_schema_version") or "").strip() != "qs.handoff_writer.v2":
            raise QSJobError("invalid_export_package_index_input:handoff_writer_schema_invalid")

    warnings = sorted(warnings, key=lambda item: (item["code"], item["message"]))
    required_present = not any(item["artifact_type"] in {"handoff_review", "approval_summary"} and not item["present"] for item in items)

    return {
        "export_package_index_schema_version": "qs.export_package_index.v2",
        "package_kind": "qs.handoff_artifact_set",
        "status": "ready" if required_present else "warning",
        "root": str(root),
        "items": items,
        "summary": {
            "file_count": sum(1 for item in items if item["present"]),
            "required_present": required_present,
        },
        "warnings": warnings,
    }
