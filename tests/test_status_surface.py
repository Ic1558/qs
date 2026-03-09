from __future__ import annotations

import unittest

from universal_qs_engine.run_manifest import attach_artifact, create_run_manifest, transition_status
from universal_qs_engine.status_surface import build_status_payload


class StatusSurfaceTests(unittest.TestCase):
    def test_payload_fields_exist(self) -> None:
        manifest = create_run_manifest("qs.boq_generate", "prj_101")
        payload = build_status_payload(manifest)
        self.assertEqual(
            set(payload),
            {
                "run_id",
                "job_type",
                "project_id",
                "status",
                "requires_approval",
                "artifacts",
                "started_at",
                "finished_at",
            },
        )

    def test_payload_matches_manifest_data(self) -> None:
        manifest = create_run_manifest("qs.report_export", "prj_102")
        manifest = transition_status(manifest, "queued")
        manifest = attach_artifact(manifest, "summary_report", "outputs/prj_102/report.pdf")
        payload = build_status_payload(manifest)

        self.assertEqual(payload["run_id"], manifest.run_id)
        self.assertEqual(payload["job_type"], "qs.report_export")
        self.assertEqual(payload["project_id"], "prj_102")
        self.assertEqual(payload["status"], "queued")
        self.assertEqual(
            payload["artifacts"],
            [
                {
                    "artifact_type": "summary_report",
                    "path": "outputs/prj_102/report.pdf",
                    "created_at": manifest.started_at,
                }
            ],
        )

    def test_approval_flag_reflects_job_contract(self) -> None:
        po_manifest = create_run_manifest("qs.po_generate", "prj_103")
        boq_manifest = create_run_manifest("qs.boq_generate", "prj_104")

        self.assertTrue(build_status_payload(po_manifest)["requires_approval"])
        self.assertFalse(build_status_payload(boq_manifest)["requires_approval"])


if __name__ == "__main__":
    unittest.main()
