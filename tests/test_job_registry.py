from __future__ import annotations

import unittest

from universal_qs_engine.job_registry import (
    UnknownQSJobError,
    get_job_handler,
    run_registered_job,
)
from universal_qs_engine.jobs._common import QSJobError


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
        self.assertEqual(
            first["artifact_refs"][0]["path"],
            "artifacts/cost/run_cost_1/cost_breakdown.json",
        )


if __name__ == "__main__":
    unittest.main()
