from __future__ import annotations

import unittest

from universal_qs_engine.job_contracts import UnknownJobContractError
from universal_qs_engine.run_manifest import (
    RunManifest,
    attach_artifact,
    create_run_manifest,
    transition_status,
)


class RunManifestTests(unittest.TestCase):
    def test_create_run_manifest_uses_job_contract_defaults(self) -> None:
        manifest = create_run_manifest("qs.boq_generate", "prj_001")
        self.assertIsInstance(manifest, RunManifest)
        self.assertEqual(manifest.run_id, "prj_001__boq_generate")
        self.assertEqual(manifest.status, "submitted")
        self.assertFalse(manifest.requires_approval)
        self.assertEqual(manifest.artifacts, ())
        self.assertIsNone(manifest.finished_at)

    def test_unknown_job_type_fails_closed(self) -> None:
        with self.assertRaises(UnknownJobContractError):
            create_run_manifest("qs.unknown_job", "prj_001")

    def test_status_transitions_are_enforced(self) -> None:
        manifest = create_run_manifest("qs.report_export", "prj_002")
        queued = transition_status(manifest, "queued")
        running = transition_status(queued, "running")
        completed = transition_status(running, "completed")
        self.assertEqual(completed.status, "completed")
        self.assertIsNotNone(completed.finished_at)

        with self.assertRaises(ValueError):
            transition_status(manifest, "completed")

    def test_artifacts_attach_deterministically(self) -> None:
        manifest = create_run_manifest("qs.compliance_check", "prj_003")
        updated = attach_artifact(manifest, "compliance_report_json", "outputs/prj_003/report.json")
        again = attach_artifact(updated, "run_manifest", "outputs/prj_003/run_manifest.json")

        self.assertEqual(
            [artifact.to_dict() for artifact in again.artifacts],
            [
                {
                    "artifact_type": "compliance_report_json",
                    "path": "outputs/prj_003/report.json",
                    "created_at": manifest.started_at,
                },
                {
                    "artifact_type": "run_manifest",
                    "path": "outputs/prj_003/run_manifest.json",
                    "created_at": manifest.started_at,
                },
            ],
        )


if __name__ == "__main__":
    unittest.main()
