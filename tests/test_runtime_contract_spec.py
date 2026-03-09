from __future__ import annotations

import unittest

from universal_qs_engine.queue_transport import build_queue_result_message
from universal_qs_engine.result_envelope import build_result_envelope
from universal_qs_engine.run_manifest import create_run_manifest, transition_status
from universal_qs_engine.runtime_transport_adapter import build_runtime_transport_payload


class RuntimeContractSpecTests(unittest.TestCase):
    def test_runtime_transport_payload_dict_matches_documented_schema_keys(self) -> None:
        manifest = create_run_manifest("qs.boq_generate", "prj_501")
        manifest = transition_status(manifest, "queued")
        manifest = transition_status(manifest, "running")
        manifest = transition_status(manifest, "completed")
        envelope = build_result_envelope(
            manifest,
            expected_outputs=("boq_json", "internal_trace_xlsx", "run_manifest"),
        )
        message = build_queue_result_message(envelope)
        payload = build_runtime_transport_payload(message).to_dict()

        self.assertEqual(
            set(payload.keys()),
            {"kind", "run_id", "job_type", "project_id", "status", "body"},
        )


if __name__ == "__main__":
    unittest.main()
