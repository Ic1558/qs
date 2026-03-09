from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from universal_qs_engine.errors import QSJobError
from universal_qs_engine.job_registry import run_registered_job
from universal_qs_engine.report_generate_v2 import compose_report_v2


class ReportGenerateV2Tests(unittest.TestCase):
    def _write_json(self, directory: Path, name: str, payload: dict) -> Path:
        path = directory / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_compose_report_v2_success_and_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            boq = self._write_json(root, "boq.json", {"items": [{"x": 1}, {"x": 2}]})
            estimate = self._write_json(
                root,
                "estimate.json",
                {
                    "estimate_id": "estimate_001",
                    "line_items": [{"item_code": "paint", "quantity": 5, "unit": "m2", "unit_price": 300}],
                    "total_cost": 1500,
                    "currency": "THB",
                },
            )
            po = self._write_json(
                root,
                "po.json",
                {
                    "vendor": {"vendor_id": "vendor_001"},
                    "line_items": [{"item_code": "paint"}],
                    "total_cost": 1500,
                    "currency": "THB",
                },
            )
            first = compose_report_v2(
                boq_ref=str(boq),
                estimate_ref=str(estimate),
                po_ref=str(po),
                report_profile_id="default_qs_v2",
            )
            second = compose_report_v2(
                boq_ref=str(boq),
                estimate_ref=str(estimate),
                po_ref=str(po),
                report_profile_id="default_qs_v2",
            )
            self.assertEqual(first, second)
            self.assertEqual(first["report_schema_version"], "qs.report_generate.v2")
            self.assertEqual(first["summary"]["boq_items"], 2)
            self.assertEqual(first["sections"][0], "executive_summary")
            self.assertEqual(first["warnings"], [])

    def test_rejects_non_json_refs(self) -> None:
        with self.assertRaises(QSJobError):
            compose_report_v2(
                boq_ref="/tmp/boq.csv",
                estimate_ref="/tmp/estimate.json",
                po_ref="/tmp/po.json",
                report_profile_id="default_qs_v2",
            )

    def test_job_embeds_report_details_for_explicit_v2_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            boq = self._write_json(root, "boq.json", {"items": []})
            estimate = self._write_json(
                root,
                "estimate.json",
                {"estimate_id": "estimate_001", "line_items": [], "total_cost": 0, "currency": "THB"},
            )
            po = self._write_json(
                root,
                "po.json",
                {"vendor": {"vendor_id": "vendor_001"}, "line_items": [], "total_cost": 0, "currency": "THB"},
            )
            result = run_registered_job(
                "qs.report_generate",
                {
                    "run_id": "run_report_v2_001",
                    "project_id": "prj_report_v2_001",
                    "inputs": {
                        "boq_ref": str(boq),
                        "estimate_ref": str(estimate),
                        "po_ref": str(po),
                        "report_profile_id": "default_qs_v2",
                    },
                },
            )
            self.assertEqual(result["details"]["report_generate"]["report_profile_id"], "default_qs_v2")

    def test_v1_compatibility_minimal_context_still_runs(self) -> None:
        result = run_registered_job(
            "qs.report_export",
            {"run_id": "run_v1_report", "project_id": "prj_v1"},
        )
        self.assertEqual(result["job_type"], "qs.report_generate")
        self.assertIn("artifact_refs", result)


if __name__ == "__main__":
    unittest.main()

