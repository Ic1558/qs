from __future__ import annotations

from typing import Any

from ..boq_extractor_v2 import extract_boq_v2
from ._common import artifact_ref, require_context_value


def run(context: dict[str, Any]) -> dict[str, Any]:
    run_id = require_context_value(context, "run_id")
    _ = require_context_value(context, "project_id")
    inputs = context.get("inputs")
    details: dict[str, Any] = {"output_profile": "boq_extract_v2"}
    if isinstance(inputs, dict) and inputs:
        details["boq_extract"] = extract_boq_v2(
            source_ref=str(inputs["source_ref"]),
            measurement_system=str(inputs.get("measurement_system") or "metric"),
        )
    return {
        "job_type": "qs.boq_extract",
        "details": details,
        "artifact_refs": [
            artifact_ref(run_id, "boq", "quantities.json", "structured_quantities"),
        ],
    }
