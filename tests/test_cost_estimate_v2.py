from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from universal_qs_engine.cost_estimate_v2 import estimate_cost_v2
from universal_qs_engine.errors import QSJobError
from universal_qs_engine.job_registry import run_registered_job


class CostEstimateV2Tests(unittest.TestCase):
    def _write_json(self, directory: Path, name: str, payload: dict) -> Path:
        path = directory / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_estimates_cost_from_snapshot_refs_deterministically(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            boq = self._write_json(
                root,
                "boq.json",
                {
                    "items": [
                        {"item_code": "concrete", "description": "Concrete", "quantity": 10, "unit": "m3"},
                        {"item_code": "steel", "description": "Steel", "quantity": 2, "unit": "ton"},
                    ]
                },
            )
            rates = self._write_json(
                root,
                "rates.json",
                {
                    "rates": [
                        {"item_code": "steel", "unit": "ton", "unit_price": 25000},
                        {"item_code": "concrete", "unit": "m3", "unit_price": 2400},
                    ]
                },
            )
            first = estimate_cost_v2(boq_ref=str(boq), price_snapshot_ref=str(rates))
            second = estimate_cost_v2(boq_ref=str(boq), price_snapshot_ref=str(rates))
            self.assertEqual(first, second)
            self.assertEqual(first["cost_schema_version"], "qs.cost_estimate.v2")
            self.assertEqual(first["total_cost"], 74000.0)
            self.assertEqual([item["item_code"] for item in first["line_items"]], ["concrete", "steel"])

    def test_rejects_missing_rate(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            boq = self._write_json(root, "boq.json", {"items": [{"item_code": "concrete", "quantity": 1, "unit": "m3"}]})
            rates = self._write_json(root, "rates.json", {"rates": []})
            with self.assertRaises(QSJobError):
                estimate_cost_v2(boq_ref=str(boq), price_snapshot_ref=str(rates))

    def test_job_embeds_cost_estimate_details_for_explicit_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            boq = self._write_json(root, "boq.json", {"items": [{"item_code": "paint", "quantity": 5, "unit": "m2"}]})
            rates = self._write_json(root, "rates.json", {"rates": [{"item_code": "paint", "unit": "m2", "unit_price": 300}]})
            result = run_registered_job(
                "qs.cost_estimate",
                {
                    "run_id": "run_cost_v2_001",
                    "project_id": "prj_cost_v2_001",
                    "inputs": {
                        "boq_ref": str(boq),
                        "price_snapshot_ref": str(rates),
                        "currency": "THB",
                    },
                },
            )
            self.assertEqual(result["details"]["cost_estimate"]["total_cost"], 1500.0)


if __name__ == "__main__":
    unittest.main()
