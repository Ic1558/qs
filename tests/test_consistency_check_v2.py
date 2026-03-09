from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from universal_qs_engine.consistency_check_v2 import check_consistency_v2
from universal_qs_engine.errors import QSJobError


class ConsistencyCheckV2Tests(unittest.TestCase):
    def _write_json(self, directory: Path, name: str, payload: dict) -> Path:
        path = directory / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_success_path_with_structurally_valid_refs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            boq = self._write_json(root, "boq.json", {"items": [{"item_code": "A1", "quantity": 2}]})
            estimate = self._write_json(
                root,
                "estimate.json",
                {"line_items": [{"item_code": "A1", "quantity": 2}], "total_cost": 1000.0},
            )
            po = self._write_json(
                root,
                "po.json",
                {
                    "vendor": {"vendor_id": "vendor_001"},
                    "line_items": [{"item_code": "A1"}],
                    "total_cost": 1000.0,
                },
            )
            result = check_consistency_v2(str(boq), str(estimate), str(po))
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["warnings"], [])
            self.assertEqual(result["summary"]["boq_items"], 1)

    def test_reject_non_json_refs(self) -> None:
        with self.assertRaises(QSJobError):
            check_consistency_v2("/tmp/boq.csv", "/tmp/estimate.json", "/tmp/po.json")

    def test_reject_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            estimate = self._write_json(root, "estimate.json", {"line_items": [], "total_cost": 0})
            po = self._write_json(
                root,
                "po.json",
                {"vendor": {"vendor_id": "vendor_001"}, "line_items": [], "total_cost": 0},
            )
            with self.assertRaises(QSJobError):
                check_consistency_v2(str(root / "boq.json"), str(estimate), str(po))

    def test_reject_malformed_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            boq = root / "boq.json"
            boq.write_text("{bad-json", encoding="utf-8")
            estimate = self._write_json(root, "estimate.json", {"line_items": [], "total_cost": 0})
            po = self._write_json(
                root,
                "po.json",
                {"vendor": {"vendor_id": "vendor_001"}, "line_items": [], "total_cost": 0},
            )
            with self.assertRaises(QSJobError):
                check_consistency_v2(str(boq), str(estimate), str(po))

    def test_warning_when_estimate_total_differs_from_po_total(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            boq = self._write_json(root, "boq.json", {"items": [{"item_code": "A1", "quantity": 2}]})
            estimate = self._write_json(
                root,
                "estimate.json",
                {"line_items": [{"item_code": "A1", "quantity": 2}], "total_cost": 1000.0},
            )
            po = self._write_json(
                root,
                "po.json",
                {
                    "vendor": {"vendor_id": "vendor_001"},
                    "line_items": [{"item_code": "A1"}],
                    "total_cost": 999.0,
                },
            )
            result = check_consistency_v2(str(boq), str(estimate), str(po))
            self.assertEqual(result["status"], "warning")
            self.assertEqual(result["warnings"][0]["code"], "estimate_po_total_cost_mismatch")

    def test_warning_when_item_counts_differ(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            boq = self._write_json(
                root,
                "boq.json",
                {"items": [{"item_code": "A1", "quantity": 2}, {"item_code": "A2", "quantity": 1}]},
            )
            estimate = self._write_json(
                root,
                "estimate.json",
                {"line_items": [{"item_code": "A1", "quantity": 2}], "total_cost": 1000.0},
            )
            po = self._write_json(
                root,
                "po.json",
                {
                    "vendor": {"vendor_id": "vendor_001"},
                    "line_items": [{"item_code": "A1"}],
                    "total_cost": 1000.0,
                },
            )
            result = check_consistency_v2(str(boq), str(estimate), str(po))
            self.assertEqual(result["status"], "warning")
            self.assertEqual(result["warnings"][0]["code"], "boq_estimate_code_gap")
            self.assertEqual(result["warnings"][1]["code"], "boq_estimate_item_count_mismatch")

    def test_warning_ordering_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            boq = self._write_json(
                root,
                "boq.json",
                {"items": [{"item_code": "B2", "quantity": 3}, {"item_code": "A1", "quantity": 2}]},
            )
            estimate = self._write_json(
                root,
                "estimate.json",
                {"line_items": [{"item_code": "A1", "quantity": 2}], "total_cost": 1000.0},
            )
            po = self._write_json(
                root,
                "po.json",
                {
                    "vendor": {"vendor_id": "vendor_001"},
                    "line_items": [],
                    "total_cost": 900.0,
                },
            )
            first = check_consistency_v2(str(boq), str(estimate), str(po))
            second = check_consistency_v2(str(boq), str(estimate), str(po))
            self.assertEqual(first["warnings"], second["warnings"])
            self.assertEqual(
                [item["code"] for item in first["warnings"]],
                [
                    "boq_estimate_code_gap",
                    "boq_estimate_item_count_mismatch",
                    "estimate_po_item_count_mismatch",
                    "estimate_po_total_cost_mismatch",
                ],
            )


if __name__ == "__main__":
    unittest.main()
