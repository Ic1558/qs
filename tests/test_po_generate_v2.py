from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from universal_qs_engine.errors import QSJobError
from universal_qs_engine.job_registry import run_registered_job
from universal_qs_engine.po_generate_v2 import generate_po_v2


class POGenerateV2Tests(unittest.TestCase):
    def _write_json(self, directory: Path, name: str, payload: dict) -> Path:
        path = directory / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_generates_deterministic_po_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            estimate = self._write_json(
                root,
                "estimate.json",
                {
                    "estimate_id": "estimate_001",
                    "line_items": [
                        {"item_code": "steel", "description": "Steel", "quantity": 2, "unit": "ton", "unit_price": 25000},
                        {"item_code": "concrete", "description": "Concrete", "quantity": 10, "unit": "m3", "unit_price": 2400},
                    ],
                    "total_cost": 74000,
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
            first = generate_po_v2(
                estimate_ref=str(estimate),
                vendor_ref=str(vendor),
                terms_template_id="template://po_standard_v1",
            )
            second = generate_po_v2(
                estimate_ref=str(estimate),
                vendor_ref=str(vendor),
                terms_template_id="template://po_standard_v1",
            )
            self.assertEqual(first, second)
            self.assertEqual(first["po_schema_version"], "qs.po_generate.v2")
            self.assertEqual(first["line_items"][0]["item_code"], "concrete")
            self.assertEqual(first["total_cost"], 74000.0)

    def test_rejects_missing_vendor_terms(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            estimate = self._write_json(
                root,
                "estimate.json",
                {"estimate_id": "estimate_001", "line_items": [], "total_cost": 0},
            )
            vendor = self._write_json(
                root,
                "vendor.json",
                {"vendor_id": "vendor_001", "vendor_name": "Acme Supply"},
            )
            with self.assertRaises(QSJobError):
                generate_po_v2(
                    estimate_ref=str(estimate),
                    vendor_ref=str(vendor),
                    terms_template_id="template://po_standard_v1",
                )

    def test_job_embeds_po_details_for_explicit_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            estimate = self._write_json(
                root,
                "estimate.json",
                {
                    "estimate_id": "estimate_001",
                    "line_items": [
                        {"item_code": "paint", "description": "Paint", "quantity": 5, "unit": "m2", "unit_price": 300}
                    ],
                    "total_cost": 1500,
                },
            )
            vendor = self._write_json(
                root,
                "vendor.json",
                {
                    "vendor_id": "vendor_001",
                    "vendor_name": "Acme Supply",
                    "payment_terms": "15 days",
                },
            )
            result = run_registered_job(
                "qs.po_generate",
                {
                    "run_id": "run_po_v2_001",
                    "project_id": "prj_po_v2_001",
                    "inputs": {
                        "estimate_ref": str(estimate),
                        "vendor_ref": str(vendor),
                        "terms_template_id": "template://po_standard_v1",
                    },
                },
            )
            self.assertEqual(result["details"]["po_generate"]["vendor"]["vendor_name"], "Acme Supply")


if __name__ == "__main__":
    unittest.main()
