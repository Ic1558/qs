from __future__ import annotations

import unittest

from universal_qs_engine.queue_transport import build_queue_result_message
from universal_qs_engine.result_envelope import build_result_envelope
from universal_qs_engine.run_manifest import create_run_manifest, transition_status
from universal_qs_engine.runtime_transport_adapter import build_runtime_transport_payload
from universal_qs_engine.zero_luka_bridge_adapter import build_0luka_bridge_payload


class ZeroLukaBridgeDeliveryContractTests(unittest.TestCase):
    def test_bridge_delivery_payload_dict_matches_documented_schema_keys(self) -> None:
        manifest = create_run_manifest("qs.boq_generate", "prj_701")
        manifest = transition_status(manifest, "queued")
        manifest = transition_status(manifest, "running")
        manifest = transition_status(manifest, "completed")
        envelope = build_result_envelope(
            manifest,
            expected_outputs=("boq_json", "internal_trace_xlsx", "run_manifest"),
        )
        message = build_queue_result_message(envelope)
        runtime_payload = build_runtime_transport_payload(message)
        bridge_payload = build_0luka_bridge_payload(runtime_payload).to_dict()

        self.assertEqual(
            set(bridge_payload.keys()),
            {"kind", "bridge_kind", "run_id", "job_type", "project_id", "status", "payload"},
        )


if __name__ == "__main__":
    unittest.main()
