from __future__ import annotations

import unittest
from dataclasses import replace

from universal_qs_engine.queue_transport import build_queue_result_message
from universal_qs_engine.result_envelope import ResultEnvelopeError, build_result_envelope
from universal_qs_engine.run_manifest import create_run_manifest, transition_status
from universal_qs_engine.runtime_transport_adapter import (
    RuntimeTransportAdapterError,
    build_runtime_transport_payload,
)
from universal_qs_engine.zero_luka_bridge_adapter import (
    ZeroLukaBridgeAdapterError,
    build_0luka_bridge_payload,
)


class ZeroLukaBridgeDryRunSimulationTests(unittest.TestCase):
    def _build_bridge_payload(self, job_type: str, project_id: str, terminal_status: str):
        manifest = create_run_manifest(job_type, project_id)
        manifest = transition_status(manifest, "queued")
        manifest = transition_status(manifest, "running")
        manifest = transition_status(manifest, terminal_status)

        expected_outputs_by_job = {
            "qs.boq_generate": ("boq_json", "internal_trace_xlsx", "run_manifest"),
            "qs.compliance_check": ("compliance_report_json", "gate_summary", "run_manifest"),
            "qs.po_generate": ("po_package", "po_manifest", "run_manifest"),
            "qs.report_export": ("summary_report", "export_bundle", "run_manifest"),
        }

        error_fields = {}
        if terminal_status == "failed":
            error_fields = {
                "error_code": "simulation_failed",
                "error_message": f"{job_type} failed in dry run",
            }
        elif terminal_status == "rejected":
            error_fields = {
                "error_code": "simulation_rejected",
                "error_message": f"{job_type} rejected in dry run",
            }

        envelope = build_result_envelope(
            manifest,
            expected_outputs=expected_outputs_by_job[job_type],
            **error_fields,
        )
        message = build_queue_result_message(envelope)
        runtime_payload = build_runtime_transport_payload(message)
        return manifest, build_0luka_bridge_payload(runtime_payload)

    def test_completed_failed_and_rejected_cases_flow_end_to_end(self) -> None:
        cases = [
            ("qs.boq_generate", "prj_801", "completed"),
            ("qs.compliance_check", "prj_802", "failed"),
            ("qs.po_generate", "prj_803", "rejected"),
        ]

        for job_type, project_id, status in cases:
            with self.subTest(job_type=job_type, status=status):
                manifest, bridge_payload = self._build_bridge_payload(job_type, project_id, status)
                payload = bridge_payload.to_dict()

                self.assertEqual(payload["bridge_kind"], "0luka.bridge_result")
                self.assertEqual(payload["run_id"], manifest.run_id)
                self.assertEqual(payload["job_type"], manifest.job_type)
                self.assertEqual(payload["project_id"], manifest.project_id)
                self.assertEqual(payload["status"], manifest.status)
                self.assertEqual(
                    set(payload.keys()),
                    {"kind", "bridge_kind", "run_id", "job_type", "project_id", "status", "payload"},
                )
                self.assertEqual(payload["payload"]["run_id"], manifest.run_id)
                self.assertEqual(payload["payload"]["status"], manifest.status)
                self.assertEqual(payload["payload"]["body"]["run_id"], manifest.run_id)

    def test_determinism_same_input_same_delivery_unit(self) -> None:
        _, payload_a = self._build_bridge_payload("qs.report_export", "prj_804", "completed")
        _, payload_b = self._build_bridge_payload("qs.report_export", "prj_804", "completed")
        self.assertEqual(payload_a.to_dict(), payload_b.to_dict())

    def test_rejects_malformed_units_in_simulation(self) -> None:
        manifest = create_run_manifest("qs.compliance_check", "prj_805")
        manifest = transition_status(manifest, "queued")
        manifest = transition_status(manifest, "running")
        manifest = transition_status(manifest, "failed")

        envelope = build_result_envelope(
            manifest,
            expected_outputs=("compliance_report_json", "gate_summary", "run_manifest"),
            error_code="simulation_failed",
            error_message="dry run failed",
        )
        message = build_queue_result_message(envelope)
        runtime_payload = build_runtime_transport_payload(message)

        with self.assertRaises(ZeroLukaBridgeAdapterError):
            build_0luka_bridge_payload(replace(runtime_payload, run_id=""))

        with self.assertRaises(ZeroLukaBridgeAdapterError):
            build_0luka_bridge_payload(replace(runtime_payload, body=None))

        with self.assertRaises(RuntimeTransportAdapterError):
            build_runtime_transport_payload(replace(message, run_id=""))

        non_terminal_manifest = create_run_manifest("qs.boq_generate", "prj_806")
        with self.assertRaises(ResultEnvelopeError):
            build_result_envelope(
                non_terminal_manifest,
                expected_outputs=("boq_json", "internal_trace_xlsx", "run_manifest"),
            )

    def test_source_inputs_are_not_mutated(self) -> None:
        manifest = create_run_manifest("qs.boq_generate", "prj_807")
        manifest = transition_status(manifest, "queued")
        manifest = transition_status(manifest, "running")
        manifest = transition_status(manifest, "completed")

        envelope = build_result_envelope(
            manifest,
            expected_outputs=("boq_json", "internal_trace_xlsx", "run_manifest"),
        )
        message = build_queue_result_message(envelope)
        runtime_payload = build_runtime_transport_payload(message)
        before = runtime_payload.to_dict()

        build_0luka_bridge_payload(runtime_payload)

        self.assertEqual(runtime_payload.to_dict(), before)


if __name__ == "__main__":
    unittest.main()
