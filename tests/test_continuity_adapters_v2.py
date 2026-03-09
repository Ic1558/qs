from __future__ import annotations

import unittest

from universal_qs_engine.continuity_adapters_v2 import (
    make_cost_input_from_boq_v2,
    make_po_input_from_estimate_v2,
)
from universal_qs_engine.errors import QSJobError


class ContinuityAdaptersV2Tests(unittest.TestCase):
    def test_valid_boq_payload_converts_into_deterministic_cost_input(self) -> None:
        boq_payload = {
            "normalized_quantities": [
                {"category": "slab", "measurements": {"area_m2": 100.0}},
                {"category": "beam", "measurements": {"length_m": 5.0}},
            ]
        }
        first = make_cost_input_from_boq_v2(boq_payload, "/tmp/rates.json")
        second = make_cost_input_from_boq_v2(boq_payload, "/tmp/rates.json")
        self.assertEqual(first, second)
        self.assertEqual(
            first["boq_ref_payload"]["items"],
            [
                {"item_code": "beam", "description": "beam", "quantity": 5.0, "unit": "m"},
                {"item_code": "slab", "description": "slab", "quantity": 100.0, "unit": "m2"},
            ],
        )

    def test_malformed_boq_payload_fails_closed(self) -> None:
        with self.assertRaises(QSJobError):
            make_cost_input_from_boq_v2({"normalized_quantities": [{}]}, "/tmp/rates.json")

    def test_valid_estimate_payload_converts_into_deterministic_po_input(self) -> None:
        estimate_payload = {
            "currency": "THB",
            "line_items": [
                {"item_code": "slab", "description": "slab", "quantity": 100.0, "unit": "m2", "unit_price": 1200.0},
                {"item_code": "beam", "description": "beam", "quantity": 5.0, "unit": "m", "unit_price": 800.0},
            ],
            "total_cost": 124000.0,
            "source_snapshot": {"boq_ref": "/tmp/boq.json"},
        }
        first = make_po_input_from_estimate_v2(estimate_payload, "/tmp/vendor.json", "template://po_standard_v1")
        second = make_po_input_from_estimate_v2(estimate_payload, "/tmp/vendor.json", "template://po_standard_v1")
        self.assertEqual(first, second)
        self.assertTrue(first["estimate_ref_payload"]["estimate_id"].startswith("estimate_auto_"))
        self.assertEqual(
            [item["item_code"] for item in first["estimate_ref_payload"]["line_items"]],
            ["beam", "slab"],
        )

    def test_malformed_estimate_payload_fails_closed(self) -> None:
        with self.assertRaises(QSJobError):
            make_po_input_from_estimate_v2({"line_items": [], "total_cost": "bad"}, "/tmp/vendor.json", "template://po_standard_v1")

    def test_continuity_adapters_preserve_deterministic_ordering(self) -> None:
        estimate_payload = {
            "line_items": [
                {"item_code": "zinc", "description": "zinc", "quantity": 1.0, "unit": "kg", "unit_price": 10.0},
                {"item_code": "beam", "description": "beam", "quantity": 2.0, "unit": "m", "unit_price": 20.0},
            ],
            "total_cost": 50.0,
        }
        result = make_po_input_from_estimate_v2(estimate_payload, "/tmp/vendor.json", "template://po_standard_v1")
        self.assertEqual(
            [item["item_code"] for item in result["estimate_ref_payload"]["line_items"]],
            ["beam", "zinc"],
        )


if __name__ == "__main__":
    unittest.main()
