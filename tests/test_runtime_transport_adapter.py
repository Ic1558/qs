from __future__ import annotations

import unittest
from dataclasses import replace

from universal_qs_engine.queue_transport import build_queue_result_message
from universal_qs_engine.result_envelope import build_result_envelope
from universal_qs_engine.run_manifest import create_run_manifest, transition_status
from universal_qs_engine.runtime_transport_adapter import (
    RuntimeTransportAdapterError,
    build_runtime_transport_payload,
)


class RuntimeTransportAdapterTests(unittest.TestCase):
    def test_completed_message_maps_to_runtime_transport_payload(self) -> None:
        manifest = create_run_manifest("qs.boq_generate", "prj_401")
        manifest = transition_status(manifest, "queued")
        manifest = transition_status(manifest, "running")
        manifest = transition_status(manifest, "completed")
        envelope = build_result_envelope(
            manifest,
            expected_outputs=("boq_json", "internal_trace_xlsx", "run_manifest"),
        )
        message = build_queue_result_message(envelope)

        payload = build_runtime_transport_payload(message)
        self.assertEqual(payload.kind, "qs.runtime_result")
        self.assertEqual(payload.run_id, message.run_id)
        self.assertEqual(payload.status, "completed")
        self.assertEqual(payload.body["status"], "completed")

    def test_failed_message_maps_without_success_coercion(self) -> None:
        manifest = create_run_manifest("qs.compliance_check", "prj_402")
        manifest = transition_status(manifest, "queued")
        manifest = transition_status(manifest, "running")
        manifest = transition_status(manifest, "failed")
        envelope = build_result_envelope(
            manifest,
            expected_outputs=("compliance_report_json", "gate_summary", "run_manifest"),
            error_code="compliance_failed",
            error_message="Compliance failed",
        )
        message = build_queue_result_message(envelope)

        payload = build_runtime_transport_payload(message)
        self.assertEqual(payload.status, "failed")
        self.assertEqual(payload.body["outcome_classification"], "failure")

    def test_payload_dict_is_deterministic_and_minimal(self) -> None:
        manifest = create_run_manifest("qs.report_export", "prj_403")
        manifest = transition_status(manifest, "queued")
        manifest = transition_status(manifest, "running")
        manifest = transition_status(manifest, "rejected")
        envelope = build_result_envelope(
            manifest,
            expected_outputs=("summary_report", "export_bundle", "run_manifest"),
            error_code="run_rejected",
            error_message="Report rejected",
        )
        message = build_queue_result_message(envelope)

        payload_a = build_runtime_transport_payload(message).to_dict()
        payload_b = build_runtime_transport_payload(message).to_dict()
        self.assertEqual(payload_a, payload_b)
        self.assertEqual(
            set(payload_a),
            {"kind", "run_id", "job_type", "project_id", "status", "body"},
        )

    def test_broken_identity_fails_closed(self) -> None:
        manifest = create_run_manifest("qs.po_generate", "prj_404")
        manifest = transition_status(manifest, "queued")
        manifest = transition_status(manifest, "running")
        manifest = transition_status(manifest, "rejected")
        envelope = build_result_envelope(
            manifest,
            expected_outputs=("po_package", "po_manifest", "run_manifest"),
            error_code="run_rejected",
            error_message="PO rejected",
        )
        message = build_queue_result_message(envelope)
        broken = replace(message, run_id="")

        with self.assertRaises(RuntimeTransportAdapterError):
            build_runtime_transport_payload(broken)

    def test_source_message_is_not_mutated(self) -> None:
        manifest = create_run_manifest("qs.boq_generate", "prj_405")
        manifest = transition_status(manifest, "queued")
        manifest = transition_status(manifest, "running")
        manifest = transition_status(manifest, "completed")
        envelope = build_result_envelope(
            manifest,
            expected_outputs=("boq_json", "internal_trace_xlsx", "run_manifest"),
        )
        message = build_queue_result_message(envelope)
        before = message.to_dict()

        build_runtime_transport_payload(message)

        self.assertEqual(message.to_dict(), before)


if __name__ == "__main__":
    unittest.main()
