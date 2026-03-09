from __future__ import annotations

from typing import Any

from ._common import artifact_ref, require_context_value


def run(context: dict[str, Any]) -> dict[str, Any]:
    run_id = require_context_value(context, "run_id")
    _ = require_context_value(context, "project_id")
    return {
        "job_type": "qs.report_generate",
        "artifact_refs": [
            artifact_ref(run_id, "report", "project_qs_report.md", "summary_report"),
        ],
    }
