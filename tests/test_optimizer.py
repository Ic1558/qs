from __future__ import annotations

import json
import unittest
from pathlib import Path

from universal_qs_engine.contracts import TakeoffRequest
from universal_qs_engine.optimizer import build_optimization_plan


ROOT = Path(__file__).resolve().parents[1]


class OptimizerTests(unittest.TestCase):
    def test_optimizer_prefers_vector_sources(self) -> None:
        payload = json.loads((ROOT / "examples" / "request.json").read_text(encoding="utf-8"))
        request = TakeoffRequest.from_dict(payload)
        plan = build_optimization_plan(request, review_required=True)
        actions = {item["action"] for item in plan["actions"]}
        self.assertIn("prefer_vector_sources", actions)
        self.assertIn("defer_full_xlsx_export", actions)

    def test_optimizer_sets_medium_profile_for_mixed_sources(self) -> None:
        payload = json.loads((ROOT / "examples" / "request.json").read_text(encoding="utf-8"))
        request = TakeoffRequest.from_dict(payload)
        plan = build_optimization_plan(request, review_required=True)
        self.assertEqual(plan["estimated_cost_profile"], "medium")


if __name__ == "__main__":
    unittest.main()
