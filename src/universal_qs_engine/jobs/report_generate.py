from __future__ import annotations

from typing import Any

from ..bundle_manifest_v2 import build_bundle_manifest_v2
from ..consistency_check_v2 import check_consistency_v2
from ..export_package_index_v2 import build_export_package_index_v2
from ..export_profile_v2 import build_export_profile_v2
from ..handoff_review_v2 import build_handoff_review_v2
from ..handoff_writer_v2 import write_handoff_artifacts_v2
from ..report_generate_v2 import _load_json_ref, compose_report_v2
from ..release_pack_v2 import build_release_pack_from_payload
from ._common import artifact_ref, require_context_value


def run(context: dict[str, Any]) -> dict[str, Any]:
    run_id = require_context_value(context, "run_id")
    _ = require_context_value(context, "project_id")
    inputs = context.get("inputs")
    details: dict[str, Any] = {"output_profile": "report_generate_v2"}
    if isinstance(inputs, dict) and inputs and "run_manifest_ref" not in inputs:
        report_payload = compose_report_v2(
            boq_ref=str(inputs["boq_ref"]),
            estimate_ref=str(inputs["estimate_ref"]),
            po_ref=str(inputs["po_ref"]),
            report_profile_id=str(inputs["report_profile_id"]),
        )
        consistency_payload = check_consistency_v2(
            boq_ref=str(inputs["boq_ref"]),
            estimate_ref=str(inputs["estimate_ref"]),
            po_ref=str(inputs["po_ref"]),
        )
        po_payload = _load_json_ref(str(inputs["po_ref"]), ref_name="po_ref")
        release_pack_payload = build_release_pack_from_payload(
            report_payload,
            consistency_payload,
            po_payload,
        )
        details["report_generate"] = report_payload
        details["consistency_check"] = consistency_payload
        details["release_pack"] = release_pack_payload
        bundle_manifest_payload = build_bundle_manifest_v2(
            report_payload,
            consistency_payload,
            release_pack_payload,
            po_payload,
        )
        details["bundle_manifest"] = bundle_manifest_payload
        details["export_profile"] = build_export_profile_v2(
            report_payload,
            consistency_payload,
            release_pack_payload,
            bundle_manifest_payload,
            po_payload,
        )
        details["handoff_review"] = build_handoff_review_v2(
            report_payload,
            consistency_payload,
            release_pack_payload,
            bundle_manifest_payload,
            details["export_profile"],
            po_payload,
        )
        handoff_output_dir = str(inputs.get("handoff_output_dir") or "").strip()
        if handoff_output_dir:
            details["handoff_writer_result"] = write_handoff_artifacts_v2(
                handoff_output_dir,
                report_payload=report_payload,
                handoff_review_payload=details["handoff_review"],
                export_profile_payload=details["export_profile"],
                release_pack_payload=release_pack_payload,
                bundle_manifest_payload=bundle_manifest_payload,
            )
            details["export_package_index"] = build_export_package_index_v2(
                handoff_output_dir,
                details["handoff_writer_result"]["written_files"],
                handoff_writer_result=details["handoff_writer_result"],
            )
    return {
        "job_type": "qs.report_generate",
        "details": details,
        "artifact_refs": [
            artifact_ref(run_id, "report", "project_qs_report.md", "summary_report"),
        ],
    }
