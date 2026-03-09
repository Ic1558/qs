from __future__ import annotations

import unittest

from universal_qs_engine.errors import QSJobError
from universal_qs_engine.job_context import canonical_job_type, normalize_job_context


class JobContextSchemaTests(unittest.TestCase):
    def test_aliases_normalize_to_canonical_job_type(self) -> None:
        self.assertEqual(canonical_job_type("qs.boq_generate"), "qs.boq_extract")
        self.assertEqual(canonical_job_type("qs.report_export"), "qs.report_generate")

    def test_v1_minimal_context_remains_valid(self) -> None:
        normalized = normalize_job_context(
            "qs.cost_estimate",
            {"run_id": "run_001", "project_id": "prj_001"},
        )
        self.assertEqual(normalized["job_type"], "qs.cost_estimate")
        self.assertEqual(normalized["metadata"], {})
        self.assertEqual(normalized["inputs"], {})

    def test_explicit_v2_context_enforces_required_inputs(self) -> None:
        normalized = normalize_job_context(
            "qs.po_generate",
            {
                "run_id": "run_po_001",
                "project_id": "prj_po_001",
                "inputs": {
                    "estimate_ref": "estimate://001",
                    "vendor_ref": "vendor://001",
                    "terms_template_id": "template://po_v1",
                },
                "metadata": {"requested_by": "operator"},
            },
        )
        self.assertEqual(normalized["job_type"], "qs.po_generate")
        self.assertEqual(normalized["inputs"]["estimate_ref"], "estimate://001")

    def test_missing_required_input_fails_closed(self) -> None:
        with self.assertRaises(QSJobError):
            normalize_job_context(
                "qs.report_generate",
                {
                    "run_id": "run_report_001",
                    "project_id": "prj_report_001",
                    "inputs": {"artifact_bundle_ref": "bundle://001"},
                },
            )

    def test_unexpected_input_key_fails_closed(self) -> None:
        with self.assertRaises(QSJobError):
            normalize_job_context(
                "qs.boq_extract",
                {
                    "run_id": "run_boq_001",
                    "project_id": "prj_boq_001",
                    "inputs": {
                        "source_ref": "source://001",
                        "rogue": "not_allowed",
                    },
                },
            )

    def test_mismatched_context_job_type_fails_closed(self) -> None:
        with self.assertRaises(QSJobError):
            normalize_job_context(
                "qs.cost_estimate",
                {
                    "run_id": "run_cost_001",
                    "job_type": "qs.po_generate",
                    "project_id": "prj_cost_001",
                },
            )


if __name__ == "__main__":
    unittest.main()
