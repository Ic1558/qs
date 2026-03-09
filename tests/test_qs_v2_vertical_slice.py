from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from universal_qs_engine.continuity_adapters_v2 import (
    make_cost_input_from_boq_v2,
    make_po_input_from_estimate_v2,
)
from universal_qs_engine.errors import QSJobError
from universal_qs_engine.job_registry import run_registered_job
from tests.dxf_fixture import write_minimal_dxf


class QSV2VerticalSliceTests(unittest.TestCase):
    def _write_json(self, directory: Path, name: str, payload: dict) -> Path:
        path = directory / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_qs_v2_vertical_slice_happy_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            dxf = write_minimal_dxf(root / "fixture.dxf")
            price_snapshot = self._write_json(
                root,
                "rates.json",
                {
                    "rates": [
                        {"item_code": "slab", "unit": "m2", "unit_price": 1200},
                        {"item_code": "beam", "unit": "m", "unit_price": 800},
                    ]
                },
            )
            vendor = self._write_json(
                root,
                "vendor.json",
                {
                    "vendor_id": "vendor_001",
                    "vendor_name": "Acme Supply",
                    "payment_terms": "30 days",
                },
            )

            boq_result = run_registered_job(
                "qs.boq_extract",
                {
                    "run_id": "run_boq_v2_vertical",
                    "project_id": "prj_vertical",
                    "inputs": {
                        "source_ref": str(dxf),
                        "measurement_system": "metric",
                    },
                },
            )
            cost_input = make_cost_input_from_boq_v2(
                boq_result["details"]["boq_extract"],
                str(price_snapshot),
            )
            boq_ref = self._write_json(root, "boq.json", cost_input["boq_ref_payload"])

            cost_result = run_registered_job(
                "qs.cost_estimate",
                {
                    "run_id": "run_cost_v2_vertical",
                    "project_id": "prj_vertical",
                    "inputs": {
                        "boq_ref": str(boq_ref),
                        "price_snapshot_ref": cost_input["price_snapshot_ref"],
                        "currency": "THB",
                    },
                },
            )
            po_input = make_po_input_from_estimate_v2(
                cost_result["details"]["cost_estimate"],
                str(vendor),
                "template://po_standard_v1",
            )
            estimate_ref = self._write_json(root, "estimate.json", po_input["estimate_ref_payload"])

            po_result = run_registered_job(
                "qs.po_generate",
                {
                    "run_id": "run_po_v2_vertical",
                    "project_id": "prj_vertical",
                    "inputs": {
                        "estimate_ref": str(estimate_ref),
                        "vendor_ref": po_input["vendor_ref"],
                        "terms_template_id": po_input["terms_template_id"],
                    },
                },
            )
            po_ref = self._write_json(root, "po.json", po_result["details"]["po_generate"])

            report_result = run_registered_job(
                "qs.report_generate",
                {
                    "run_id": "run_report_v2_vertical",
                    "project_id": "prj_vertical",
                    "inputs": {
                        "boq_ref": str(boq_ref),
                        "estimate_ref": str(estimate_ref),
                        "po_ref": str(po_ref),
                        "report_profile_id": "default_qs_v2",
                    },
                },
            )

            self.assertEqual(boq_result["job_type"], "qs.boq_extract")
            self.assertEqual(cost_result["job_type"], "qs.cost_estimate")
            self.assertEqual(po_result["job_type"], "qs.po_generate")
            self.assertEqual(report_result["job_type"], "qs.report_generate")
            self.assertEqual(report_result["details"]["bundle_manifest"]["bundle_kind"], "qs.approval_ready_bundle")

    def test_qs_v2_vertical_slice_report_contains_all_v2_details(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            boq = self._write_json(root, "boq.json", {"items": [{"item_code": "paint", "quantity": 5, "unit": "m2"}]})
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
            first = run_registered_job(
                "qs.report_generate",
                {
                    "run_id": "run_report_v2_details_a",
                    "project_id": "prj_vertical",
                    "inputs": {
                        "boq_ref": str(boq),
                        "estimate_ref": str(estimate),
                        "po_ref": str(po),
                        "report_profile_id": "default_qs_v2",
                    },
                },
            )
            second = run_registered_job(
                "qs.report_generate",
                {
                    "run_id": "run_report_v2_details_a",
                    "project_id": "prj_vertical",
                    "inputs": {
                        "boq_ref": str(boq),
                        "estimate_ref": str(estimate),
                        "po_ref": str(po),
                        "report_profile_id": "default_qs_v2",
                    },
                },
            )

            self.assertEqual(first, second)
            self.assertIn("report_generate", first["details"])
            self.assertIn("consistency_check", first["details"])
            self.assertIn("release_pack", first["details"])
            self.assertIn("bundle_manifest", first["details"])

    def test_qs_v2_vertical_slice_fail_closed_on_malformed_cost_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            boq = self._write_json(root, "boq.json", {"items": [{"item_code": "paint", "quantity": 5, "unit": "m2"}]})
            bad_rates = self._write_json(root, "rates.json", {"rates": []})
            with self.assertRaises(QSJobError):
                run_registered_job(
                    "qs.cost_estimate",
                    {
                        "run_id": "run_cost_v2_bad",
                        "project_id": "prj_vertical",
                        "inputs": {
                            "boq_ref": str(boq),
                            "price_snapshot_ref": str(bad_rates),
                            "currency": "THB",
                        },
                    },
                )

    def test_qs_v2_vertical_slice_v1_path_unchanged(self) -> None:
        report_result = run_registered_job(
            "qs.report_export",
            {"run_id": "run_v1_report_vertical", "project_id": "prj_v1"},
        )
        self.assertEqual(report_result["job_type"], "qs.report_generate")
        self.assertIn("artifact_refs", report_result)
        self.assertNotIn("consistency_check", report_result["details"])
        self.assertNotIn("release_pack", report_result["details"])
        self.assertNotIn("bundle_manifest", report_result["details"])


if __name__ == "__main__":
    unittest.main()
