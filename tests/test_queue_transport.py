from __future__ import annotations

import unittest
from dataclasses import replace

from universal_qs_engine.queue_transport import QueueTransportError, build_queue_result_message
from universal_qs_engine.result_envelope import build_result_envelope
from universal_qs_engine.run_manifest import attach_artifact, create_run_manifest, transition_status


class QueueTransportTests(unittest.TestCase):
    def test_build_queue_result_message_from_completed_envelope(self) -> None:
        manifest = create_run_manifest("qs.boq_generate", "prj_301")
        manifest = transition_status(manifest, "queued")
        manifest = transition_status(manifest, "running")
        manifest = transition_status(manifest, "completed")
        manifest = attach_artifact(manifest, "boq_json", "outputs/prj_301/boq.json")
        envelope = build_result_envelope(
            manifest,
            expected_outputs=("boq_json", "internal_trace_xlsx", "run_manifest"),
        )

        message = build_queue_result_message(envelope)
        self.assertEqual(message.run_id, manifest.run_id)
        self.assertEqual(message.status, "completed")
        self.assertEqual(message.outcome_classification, "success")
        self.assertEqual(message.envelope_payload["status_payload"]["status"], "completed")

    def test_transport_payload_is_deterministic(self) -> None:
        manifest = create_run_manifest("qs.report_export", "prj_302")
        manifest = transition_status(manifest, "queued")
        manifest = transition_status(manifest, "running")
        manifest = transition_status(manifest, "rejected")
        envelope = build_result_envelope(
            manifest,
            expected_outputs=("summary_report", "export_bundle", "run_manifest"),
            error_code="run_rejected",
            error_message="Report export was rejected",
        )

        msg_a = build_queue_result_message(envelope).to_dict()
        msg_b = build_queue_result_message(envelope).to_dict()
        self.assertEqual(msg_a, msg_b)

    def test_rejects_envelope_missing_identity(self) -> None:
        manifest = create_run_manifest("qs.compliance_check", "prj_303")
        manifest = transition_status(manifest, "queued")
        manifest = transition_status(manifest, "running")
        manifest = transition_status(manifest, "failed")
        envelope = build_result_envelope(
            manifest,
            expected_outputs=("compliance_report_json", "gate_summary", "run_manifest"),
            error_code="compliance_failed",
            error_message="Compliance failed",
        )
        broken = replace(envelope, run_id="")

        with self.assertRaises(QueueTransportError):
            build_queue_result_message(broken)


if __name__ == "__main__":
    unittest.main()
