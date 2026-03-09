from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from universal_qs_engine.job_registry import run_registered_job


class QSV2OperatorPrepSliceTests(unittest.TestCase):
    def _write_json(self, directory: Path, name: str, payload: dict) -> Path:
        path = directory / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def _explicit_v2_result(self, root: Path, *, run_id: str) -> dict:
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
        return run_registered_job(
            "qs.report_generate",
            {
                "run_id": run_id,
                "project_id": "prj_operator_prep",
                "inputs": {
                    "boq_ref": str(boq),
                    "estimate_ref": str(estimate),
                    "po_ref": str(po),
                    "report_profile_id": "default_qs_v2",
                },
            },
        )

    def test_qs_v2_operator_prep_slice_happy_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self._explicit_v2_result(Path(tmpdir), run_id="run_operator_prep_001")
            details = result["details"]
            self.assertIn("report_generate", details)
            self.assertIn("consistency_check", details)
            self.assertIn("release_pack", details)
            self.assertIn("bundle_manifest", details)
            self.assertIn("export_profile", details)
            self.assertIn("handoff_review", details)

    def test_qs_v2_operator_prep_slice_deterministic_repeatability(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            first = self._explicit_v2_result(root, run_id="run_operator_prep_repeat")
            second = self._explicit_v2_result(root, run_id="run_operator_prep_repeat")
            self.assertEqual(first, second)

    def test_qs_v2_operator_prep_slice_safe_degradation_without_optional_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # Build minimal explicit-v2 stack through pure builder expectations by using report_export-style v1
            # unchanged path as control and explicit-v2 stack via report_generate with minimal valid inputs.
            result = run_registered_job(
                "qs.report_generate",
                {
                    "run_id": "run_operator_prep_degrade",
                    "project_id": "prj_operator_prep",
                    "inputs": {
                        "boq_ref": str(self._write_json(root, "boq.json", {"items": []})),
                        "estimate_ref": str(
                            self._write_json(
                                root,
                                "estimate.json",
                                {"estimate_id": "estimate_001", "line_items": [], "total_cost": 0, "currency": "THB"},
                            )
                        ),
                        "po_ref": str(
                            self._write_json(
                                root,
                                "po.json",
                                {"vendor": {"vendor_id": "vendor_001"}, "line_items": [], "total_cost": 0, "currency": "THB"},
                            )
                        ),
                        "report_profile_id": "default_qs_v2",
                    },
                },
            )
            details = result["details"]
            self.assertEqual(details["release_pack"]["status"], "ready")
            self.assertEqual(details["bundle_manifest"]["status"], "ready")
            self.assertEqual(details["export_profile"]["status"], "ready")
            self.assertEqual(details["handoff_review"]["status"], "ready")

    def test_qs_v2_operator_prep_slice_v1_path_unchanged(self) -> None:
        result = run_registered_job(
            "qs.report_export",
            {"run_id": "run_operator_prep_v1", "project_id": "prj_v1"},
        )
        self.assertEqual(result["job_type"], "qs.report_generate")
        self.assertIn("artifact_refs", result)
        self.assertNotIn("consistency_check", result["details"])
        self.assertNotIn("release_pack", result["details"])
        self.assertNotIn("bundle_manifest", result["details"])
        self.assertNotIn("export_profile", result["details"])
        self.assertNotIn("handoff_review", result["details"])


if __name__ == "__main__":
    unittest.main()
