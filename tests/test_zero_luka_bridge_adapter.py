from __future__ import annotations

import unittest
from dataclasses import replace

from universal_qs_engine.queue_transport import build_queue_result_message
from universal_qs_engine.result_envelope import build_result_envelope
from universal_qs_engine.run_manifest import create_run_manifest, transition_status
from universal_qs_engine.runtime_transport_adapter import build_runtime_transport_payload
from universal_qs_engine.zero_luka_bridge_adapter import (
    ZeroLukaBridgeAdapterError,
    build_0luka_bridge_payload,
)


class ZeroLukaBridgeAdapterTests(unittest.TestCase):
    def test_completed_runtime_payload_maps_to_bridge_payload(self) -> None:
        manifest = create_run_manifest("qs.boq_generate", "prj_601")
        manifest = transition_status(manifest, "queued")
        manifest = transition_status(manifest, "running")
        manifest = transition_status(manifest, "completed")
        envelope = build_result_envelope(
            manifest,
            expected_outputs=("boq_json", "internal_trace_xlsx", "run_manifest"),
        )
        message = build_queue_result_message(envelope)
        runtime_payload = build_runtime_transport_payload(message)

        bridge_payload = build_0luka_bridge_payload(runtime_payload)
        self.assertEqual(bridge_payload.kind, "qs.runtime_result")
        self.assertEqual(bridge_payload.bridge_kind, "0luka.bridge_result")
        self.assertEqual(bridge_payload.run_id, runtime_payload.run_id)
        self.assertEqual(bridge_payload.status, "completed")

    def test_failed_runtime_payload_preserves_failure_semantics(self) -> None:
        manifest = create_run_manifest("qs.compliance_check", "prj_602")
        manifest = transition_status(manifest, "queued")
        manifest = transition_status(manifest, "running")
        manifest = transition_status(manifest, "failed")
        envelope = build_result_envelope(
            manifest,
            expected_outputs=("compliance_report_json", "gate_summary", "run_manifest"),
            error_code="compliance_failed",
            error_message="Compliance failed",
        )
        runtime_payload = build_runtime_transport_payload(build_queue_result_message(envelope))

        bridge_payload = build_0luka_bridge_payload(runtime_payload)
        self.assertEqual(bridge_payload.status, "failed")
        self.assertEqual(bridge_payload.payload["body"]["outcome_classification"], "failure")

    def test_rejected_runtime_payload_preserves_rejection_semantics(self) -> None:
        manifest = create_run_manifest("qs.po_generate", "prj_603")
        manifest = transition_status(manifest, "queued")
        manifest = transition_status(manifest, "running")
        manifest = transition_status(manifest, "rejected")
        envelope = build_result_envelope(
            manifest,
            expected_outputs=("po_package", "po_manifest", "run_manifest"),
            error_code="run_rejected",
            error_message="PO rejected",
        )
        runtime_payload = build_runtime_transport_payload(build_queue_result_message(envelope))

        bridge_payload = build_0luka_bridge_payload(runtime_payload)
        self.assertEqual(bridge_payload.status, "rejected")
        self.assertEqual(bridge_payload.payload["body"]["outcome_classification"], "rejection")

    def test_bridge_payload_dict_is_deterministic_and_minimal(self) -> None:
        manifest = create_run_manifest("qs.report_export", "prj_604")
        manifest = transition_status(manifest, "queued")
        manifest = transition_status(manifest, "running")
        manifest = transition_status(manifest, "completed")
        envelope = build_result_envelope(
            manifest,
            expected_outputs=("summary_report", "export_bundle", "run_manifest"),
        )
        runtime_payload = build_runtime_transport_payload(build_queue_result_message(envelope))

        payload_a = build_0luka_bridge_payload(runtime_payload).to_dict()
        payload_b = build_0luka_bridge_payload(runtime_payload).to_dict()
        self.assertEqual(payload_a, payload_b)
        self.assertEqual(
            set(payload_a),
            {"kind", "bridge_kind", "run_id", "job_type", "project_id", "status", "payload"},
        )

    def test_broken_identity_fails_closed(self) -> None:
        manifest = create_run_manifest("qs.boq_generate", "prj_605")
        manifest = transition_status(manifest, "queued")
        manifest = transition_status(manifest, "running")
        manifest = transition_status(manifest, "completed")
        envelope = build_result_envelope(
            manifest,
            expected_outputs=("boq_json", "internal_trace_xlsx", "run_manifest"),
        )
        runtime_payload = build_runtime_transport_payload(build_queue_result_message(envelope))
        broken = replace(runtime_payload, run_id="")

        with self.assertRaises(ZeroLukaBridgeAdapterError):
            build_0luka_bridge_payload(broken)

    def test_source_runtime_payload_is_not_mutated(self) -> None:
        manifest = create_run_manifest("qs.boq_generate", "prj_606")
        manifest = transition_status(manifest, "queued")
        manifest = transition_status(manifest, "running")
        manifest = transition_status(manifest, "completed")
        envelope = build_result_envelope(
            manifest,
            expected_outputs=("boq_json", "internal_trace_xlsx", "run_manifest"),
        )
        runtime_payload = build_runtime_transport_payload(build_queue_result_message(envelope))
        before = runtime_payload.to_dict()

        build_0luka_bridge_payload(runtime_payload)

        self.assertEqual(runtime_payload.to_dict(), before)


if __name__ == "__main__":
    unittest.main()
