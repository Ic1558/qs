from __future__ import annotations

from typing import Any

from ..report_generate_v2 import compose_report_v2
from ._common import artifact_ref, require_context_value


def run(context: dict[str, Any]) -> dict[str, Any]:
    run_id = require_context_value(context, "run_id")
    _ = require_context_value(context, "project_id")
    inputs = context.get("inputs")
    details: dict[str, Any] = {"output_profile": "report_generate_v2"}
    if isinstance(inputs, dict) and inputs and "run_manifest_ref" not in inputs:
        details["report_generate"] = compose_report_v2(
            boq_ref=str(inputs["boq_ref"]),
            estimate_ref=str(inputs["estimate_ref"]),
            po_ref=str(inputs["po_ref"]),
            report_profile_id=str(inputs["report_profile_id"]),
        )
    return {
        "job_type": "qs.report_generate",
        "details": details,
        "artifact_refs": [
            artifact_ref(run_id, "report", "project_qs_report.md", "summary_report"),
        ],
    }
