from __future__ import annotations

import unittest
import os
import sys
from pathlib import Path

# Add src to sys.path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from universal_qs_engine.api import (
    project_create,
    project_members_add_typed,
    project_aggregate,
    project_rates_add,
)
from universal_qs_engine.project_store import load_project


class DisciplineAggregationTests(unittest.TestCase):
    def _create_project(self, name: str = "Aggregation Test") -> str:
        status, payload = project_create(
            {
                "name": name,
                "client": "IC",
                "site": "Bangkok",
                "factor_mode": "private",
                "overhead_rate": 0.12,
                "vat_enabled": False,
            }
        )
        self.assertEqual(status, 200)
        return payload["project"]["project_id"]

    def test_ar_wall_deduction_logic(self) -> None:
        project_id = self._create_project("AR Deduction")
        
        # 1. Add Wall
        status, payload = project_members_add_typed(project_id, "wall", {
            "member_code": "W1",
            "level": "1F",
            "wall_type": "Brick",
            "height": 3.0,
            "gross_area": 30.0,
            "basis_status": "ADOPTED_DETAIL",
            "source_ref": "A-101"
        })
        wall_id = payload["member"]["member_id"]
        
        # 2. Add Opening
        status, payload = project_members_add_typed(project_id, "opening", {
            "member_code": "D1",
            "parent_wall_id": wall_id,
            "opening_type": "Door",
            "width": 1.0,
            "height": 2.0,
            "area": 2.0,
            "count": 1,
            "source_ref": "A-101"
        })
        
        # 3. Add Finish
        status, payload = project_members_add_typed(project_id, "finish", {
            "member_code": "F1",
            "parent_member_id": wall_id,
            "finish_type": "Paint",
            "basis_status": "ADOPTED_DETAIL",
            "source_ref": "A-101"
        })
        
        # 4. Aggregate
        status, payload = project_aggregate(project_id)
        self.assertEqual(status, 200)
        
        # 5. Verify results
        project = load_project(project_id)
        wall = next(m for m in project["takeoff"]["members"] if m["member_id"] == wall_id)
        self.assertEqual(wall["net_area"], 28.0)
        self.assertEqual(len(wall["deductions"]), 1)
        
        finish = next(m for m in project["takeoff"]["members"] if m["member_code"] == "F1")
        self.assertEqual(finish["net_area"], 28.0)

    def test_mep_aggregation_creates_components(self) -> None:
        project_id = self._create_project("MEP Aggregate")
        
        # 1. Add MEP Count Item
        status, payload = project_members_add_typed(project_id, "mep_count", {
            "member_code": "P1",
            "level": "1F",
            "item_type": "Socket",
            "count": 10,
            "basis_status": "ADOPTED_DETAIL",
            "source_ref": "E-101"
        })
        
        # 2. Add MEP Run Item
        status, payload = project_members_add_typed(project_id, "mep_run", {
            "member_code": "PIPE-01",
            "level": "1F",
            "service_type": "Cold Water",
            "length": 50.0,
            "basis_status": "ADOPTED_DETAIL",
            "source_ref": "P-101"
        })
        
        # 3. Aggregate
        status, payload = project_aggregate(project_id)
        self.assertEqual(status, 200)
        
        # 4. Verify components created
        project = load_project(project_id)
        components = project["takeoff"]["components"]
        self.assertEqual(len(components), 2)
        
        socket_comp = next(c for c in components if c["component_type"] == "Socket")
        self.assertEqual(socket_comp["qty"], 10.0)
        
        pipe_comp = next(c for c in components if c["component_type"] == "Cold Water")
        self.assertEqual(pipe_comp["qty"], 50.0)


if __name__ == "__main__":
    unittest.main()
