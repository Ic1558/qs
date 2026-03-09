from __future__ import annotations

from typing import Any

from ..cost_estimate_v2 import estimate_cost_v2
from ._common import artifact_ref, require_context_value


def run(context: dict[str, Any]) -> dict[str, Any]:
    run_id = require_context_value(context, "run_id")
    _ = require_context_value(context, "project_id")
    inputs = context.get("inputs")
    details: dict[str, Any] = {"output_profile": "cost_estimate_v2"}
    if isinstance(inputs, dict) and inputs:
        details["cost_estimate"] = estimate_cost_v2(
            boq_ref=str(inputs["boq_ref"]),
            price_snapshot_ref=str(inputs["price_snapshot_ref"]),
            currency=str(inputs.get("currency") or "THB"),
        )
    return {
        "job_type": "qs.cost_estimate",
        "details": details,
        "artifact_refs": [
            artifact_ref(run_id, "cost", "cost_breakdown.json", "cost_breakdown"),
        ],
    }
