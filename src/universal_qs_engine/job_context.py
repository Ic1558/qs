from __future__ import annotations

from typing import Any

from .errors import QSJobError

_CANONICAL_JOB_TYPES = {
    "qs.boq_extract": "qs.boq_extract",
    "qs.boq_generate": "qs.boq_extract",
    "qs.cost_estimate": "qs.cost_estimate",
    "qs.po_generate": "qs.po_generate",
    "qs.report_generate": "qs.report_generate",
    "qs.report_export": "qs.report_generate",
}

_INPUT_SCHEMAS: dict[str, dict[str, tuple[str, ...]]] = {
    "qs.boq_extract": {
        "required": ("source_ref",),
        "optional": ("assumptions_ref", "measurement_system", "rate_card_id"),
    },
    "qs.cost_estimate": {
        "required": ("boq_ref", "price_snapshot_ref"),
        "optional": ("currency", "estimate_profile"),
    },
    "qs.po_generate": {
        "required": ("estimate_ref", "vendor_ref", "terms_template_id"),
        "optional": ("issue_mode",),
    },
    "qs.report_generate": {
        "required": ("run_manifest_ref",),
        "optional": ("artifact_bundle_ref", "export_profile"),
    },
}


def canonical_job_type(job_type: str) -> str:
    value = str(job_type or "").strip()
    if not value:
        raise QSJobError("missing_context:job_type")
    try:
        return _CANONICAL_JOB_TYPES[value]
    except KeyError as exc:
        raise QSJobError(f"unknown_qs_job_type:{value}") from exc


def normalize_job_context(requested_job_type: str, context: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(context, dict):
        raise QSJobError("invalid_context:not_object")

    canonical_type = canonical_job_type(requested_job_type)
    normalized = dict(context)
    context_job_type = normalized.get("job_type")
    if context_job_type is not None:
        context_canonical = canonical_job_type(str(context_job_type))
        if context_canonical != canonical_type:
            raise QSJobError(
                f"context_job_type_mismatch:{str(context_job_type).strip()}!={requested_job_type}"
            )
    normalized["job_type"] = canonical_type

    run_id = str(normalized.get("run_id") or "").strip()
    if not run_id:
        raise QSJobError("missing_context:run_id")
    normalized["run_id"] = run_id

    project_id = str(normalized.get("project_id") or "").strip()
    if not project_id:
        raise QSJobError("missing_context:project_id")
    normalized["project_id"] = project_id

    metadata = normalized.get("metadata")
    if metadata is None:
        normalized["metadata"] = {}
    elif not isinstance(metadata, dict):
        raise QSJobError("invalid_context:metadata_not_object")

    inputs = normalized.get("inputs")
    if inputs is None:
        normalized["inputs"] = {}
        return normalized
    if not isinstance(inputs, dict):
        raise QSJobError("invalid_context:inputs_not_object")

    schema = _INPUT_SCHEMAS[canonical_type]
    allowed = set(schema["required"]) | set(schema["optional"])
    for key in inputs:
        if key not in allowed:
            raise QSJobError(f"invalid_context:unexpected_input:{canonical_type}:{key}")
    for key in schema["required"]:
        value = str(inputs.get(key) or "").strip()
        if not value:
            raise QSJobError(f"invalid_context:missing_input:{canonical_type}:{key}")
    return normalized
