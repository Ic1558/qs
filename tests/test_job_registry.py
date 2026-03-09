from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from universal_qs_engine.errors import QSJobError
from universal_qs_engine.job_registry import (
    UnknownQSJobError,
    get_job_handler,
    run_registered_job,
)
from tests.dxf_fixture import write_minimal_dxf


class JobRegistryTests(unittest.TestCase):
    def test_registry_contains_product_jobs(self) -> None:
        for job_type in (
            "qs.boq_extract",
            "qs.cost_estimate",
            "qs.po_generate",
            "qs.report_generate",
        ):
            handler = get_job_handler(job_type)
            self.assertTrue(callable(handler))

    def test_registry_aliases_existing_job_types(self) -> None:
        boq_result = run_registered_job(
            "qs.boq_generate",
            {"run_id": "run_a", "project_id": "prj_a"},
        )
        report_result = run_registered_job(
            "qs.report_export",
            {"run_id": "run_b", "project_id": "prj_b"},
        )
        self.assertEqual(boq_result["job_type"], "qs.boq_extract")
        self.assertEqual(report_result["job_type"], "qs.report_generate")

    def test_unknown_job_fails_closed(self) -> None:
        with self.assertRaises(UnknownQSJobError):
            get_job_handler("qs.unknown")

    def test_context_validation_fails_closed(self) -> None:
        with self.assertRaises(QSJobError):
            run_registered_job("qs.po_generate", {"project_id": "prj_only"})

    def test_explicit_job_inputs_follow_schema_lock(self) -> None:
        with TemporaryDirectory() as tmpdir:
            fixture = write_minimal_dxf(Path(tmpdir) / "minimal_vector.dxf")
            result = run_registered_job(
                "qs.boq_extract",
                {
                    "run_id": "run_boq_v2",
                    "project_id": "prj_boq_v2",
                    "inputs": {
                        "source_ref": str(fixture),
                        "measurement_system": "metric",
                    },
                },
            )
        self.assertEqual(result["job_type"], "qs.boq_extract")

    def test_invalid_explicit_job_inputs_fail_closed(self) -> None:
        with self.assertRaises(QSJobError):
            run_registered_job(
                "qs.cost_estimate",
                {
                    "run_id": "run_cost_invalid",
                    "project_id": "prj_cost_invalid",
                    "inputs": {"boq_ref": "boq://001"},
                },
            )

    def test_cost_estimate_rejects_non_json_snapshot_refs(self) -> None:
        with self.assertRaises(QSJobError):
            run_registered_job(
                "qs.cost_estimate",
                {
                    "run_id": "run_cost_invalid_ref",
                    "project_id": "prj_cost_invalid_ref",
                    "inputs": {
                        "boq_ref": "/tmp/boq.csv",
                        "price_snapshot_ref": "/tmp/rates.json",
                    },
                },
            )

    def test_boq_extract_requires_supported_explicit_source(self) -> None:
        with self.assertRaises(QSJobError):
            run_registered_job(
                "qs.boq_extract",
                {
                    "run_id": "run_boq_invalid",
                    "project_id": "prj_boq_invalid",
                    "inputs": {"source_ref": "/tmp/input.xlsx"},
                },
            )

    def test_po_generate_rejects_non_json_vendor_ref(self) -> None:
        with self.assertRaises(QSJobError):
            run_registered_job(
                "qs.po_generate",
                {
                    "run_id": "run_po_invalid_ref",
                    "project_id": "prj_po_invalid_ref",
                    "inputs": {
                        "estimate_ref": "/tmp/estimate.json",
                        "vendor_ref": "/tmp/vendor.csv",
                        "terms_template_id": "template://po_standard_v1",
                    },
                },
            )

    def test_artifact_refs_are_deterministic(self) -> None:
        first = run_registered_job(
            "qs.cost_estimate",
            {"run_id": "run_cost_1", "project_id": "prj_cost"},
        )
        second = run_registered_job(
            "qs.cost_estimate",
            {"run_id": "run_cost_1", "project_id": "prj_cost"},
        )
        self.assertEqual(first, second)
        self.assertEqual(first["result_kind"], "qs.job_result")
        self.assertEqual(first["schema_version"], "qs.job_output.v2")
        self.assertEqual(
            first["artifact_refs"][0]["path"],
            "artifacts/cost/run_cost_1/cost_breakdown.json",
        )


if __name__ == "__main__":
    unittest.main()
