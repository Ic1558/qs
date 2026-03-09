from __future__ import annotations

from typing import Any

from ..po_generate_v2 import generate_po_v2
from ._common import artifact_ref, require_context_value


def run(context: dict[str, Any]) -> dict[str, Any]:
    run_id = require_context_value(context, "run_id")
    _ = require_context_value(context, "project_id")
    inputs = context.get("inputs")
    details: dict[str, Any] = {"output_profile": "po_generate_v2"}
    if isinstance(inputs, dict) and inputs:
        details["po_generate"] = generate_po_v2(
            estimate_ref=str(inputs["estimate_ref"]),
            vendor_ref=str(inputs["vendor_ref"]),
            terms_template_id=str(inputs["terms_template_id"]),
        )
    return {
        "job_type": "qs.po_generate",
        "details": details,
        "artifact_refs": [
            artifact_ref(run_id, "po", "po_document.md", "po_document"),
        ],
    }
