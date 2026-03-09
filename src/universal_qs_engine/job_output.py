from __future__ import annotations

from typing import Any

from .errors import QSJobError
from .job_context import canonical_job_type

JOB_OUTPUT_SCHEMA_VERSION = "qs.job_output.v2"


def _normalize_artifact_ref(raw: Any, *, canonical_type: str, index: int) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise QSJobError(f"invalid_job_output:artifact_not_object:{canonical_type}:{index}")

    artifact_type = str(raw.get("artifact_type") or "").strip()
    path = str(raw.get("path") or "").strip()
    if not artifact_type:
        raise QSJobError(f"invalid_job_output:artifact_type_required:{canonical_type}:{index}")
    if not path:
        raise QSJobError(f"invalid_job_output:artifact_path_required:{canonical_type}:{index}")

    normalized: dict[str, Any] = {
        "artifact_type": artifact_type,
        "path": path,
    }
    if "created_at" in raw:
        created_at = str(raw.get("created_at") or "").strip()
        if not created_at:
            raise QSJobError(f"invalid_job_output:artifact_created_at_blank:{canonical_type}:{index}")
        normalized["created_at"] = created_at
    if "checksum" in raw:
        checksum = str(raw.get("checksum") or "").strip()
        if not checksum:
            raise QSJobError(f"invalid_job_output:artifact_checksum_blank:{canonical_type}:{index}")
        normalized["checksum"] = checksum
    if "metadata" in raw:
        metadata = raw.get("metadata")
        if not isinstance(metadata, dict):
            raise QSJobError(f"invalid_job_output:artifact_metadata_not_object:{canonical_type}:{index}")
        normalized["metadata"] = metadata
    return normalized


def normalize_job_output(requested_job_type: str, output: dict[str, Any]) -> dict[str, Any]:
    canonical_type = canonical_job_type(requested_job_type)
    if not isinstance(output, dict):
        raise QSJobError(f"invalid_job_output:not_object:{canonical_type}")

    output_job_type = canonical_job_type(str(output.get("job_type") or canonical_type))
    if output_job_type != canonical_type:
        raise QSJobError(f"invalid_job_output:job_type_mismatch:{output_job_type}!={canonical_type}")

    raw_refs = output.get("artifact_refs")
    if not isinstance(raw_refs, list):
        raise QSJobError(f"invalid_job_output:artifact_refs_not_list:{canonical_type}")

    normalized_refs = [
        _normalize_artifact_ref(item, canonical_type=canonical_type, index=index)
        for index, item in enumerate(raw_refs)
    ]
    normalized_refs.sort(key=lambda item: (str(item["path"]), str(item["artifact_type"])))

    normalized: dict[str, Any] = {
        "job_type": canonical_type,
        "result_kind": "qs.job_result",
        "schema_version": JOB_OUTPUT_SCHEMA_VERSION,
        "artifact_refs": normalized_refs,
    }
    if "details" in output:
        details = output.get("details")
        if not isinstance(details, dict):
            raise QSJobError(f"invalid_job_output:details_not_object:{canonical_type}")
        normalized["details"] = details
    return normalized
