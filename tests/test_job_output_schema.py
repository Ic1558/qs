from __future__ import annotations

import unittest

from universal_qs_engine.errors import QSJobError
from universal_qs_engine.job_output import JOB_OUTPUT_SCHEMA_VERSION, normalize_job_output


class JobOutputSchemaTests(unittest.TestCase):
    def test_output_is_normalized_to_canonical_shape(self) -> None:
        normalized = normalize_job_output(
            "qs.report_export",
            {
                "job_type": "qs.report_generate",
                "artifact_refs": [
                    {
                        "artifact_type": "summary_report",
                        "path": "artifacts/report/run_001/project_qs_report.md",
                    }
                ],
                "details": {"output_profile": "report_generate_v2"},
            },
        )
        self.assertEqual(normalized["job_type"], "qs.report_generate")
        self.assertEqual(normalized["result_kind"], "qs.job_result")
        self.assertEqual(normalized["schema_version"], JOB_OUTPUT_SCHEMA_VERSION)

    def test_artifact_refs_are_sorted_deterministically(self) -> None:
        normalized = normalize_job_output(
            "qs.boq_extract",
            {
                "artifact_refs": [
                    {"artifact_type": "b", "path": "artifacts/boq/run_1/z.json"},
                    {"artifact_type": "a", "path": "artifacts/boq/run_1/a.json"},
                ]
            },
        )
        self.assertEqual(
            [artifact["path"] for artifact in normalized["artifact_refs"]],
            ["artifacts/boq/run_1/a.json", "artifacts/boq/run_1/z.json"],
        )

    def test_invalid_output_job_type_fails_closed(self) -> None:
        with self.assertRaises(QSJobError):
            normalize_job_output(
                "qs.cost_estimate",
                {
                    "job_type": "qs.po_generate",
                    "artifact_refs": [],
                },
            )

    def test_invalid_artifact_shape_fails_closed(self) -> None:
        with self.assertRaises(QSJobError):
            normalize_job_output(
                "qs.po_generate",
                {
                    "artifact_refs": [{"path": "artifacts/po/run_1/po.md"}],
                },
            )


if __name__ == "__main__":
    unittest.main()
