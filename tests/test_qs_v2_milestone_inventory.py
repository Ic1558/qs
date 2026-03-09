from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from universal_qs_engine.job_registry import run_registered_job


class QSV2MilestoneInventoryTests(unittest.TestCase):
    def _repo_root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    def _src_root(self) -> Path:
        return self._repo_root() / "src" / "universal_qs_engine"

    def _write_json(self, directory: Path, name: str, payload: dict) -> Path:
        path = directory / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_qs_v2_milestone_inventory_expected_review_docs_exist(self) -> None:
        review_root = self._repo_root() / "review"
        for name in (
            "QS_V2_VERTICAL_SLICE_SEAL.md",
            "QS_V2_OPERATOR_PREP_SLICE_SEAL.md",
            "QS_V2_MILESTONE_CLOSEOUT.md",
        ):
            self.assertTrue((review_root / name).exists(), msg=name)

    def test_qs_v2_milestone_inventory_expected_v2_modules_exist(self) -> None:
        src_root = self._src_root()
        for name in (
            "job_context.py",
            "job_output.py",
            "boq_extractor_v2.py",
            "cost_estimate_v2.py",
            "po_generate_v2.py",
            "report_generate_v2.py",
            "consistency_check_v2.py",
            "release_pack_v2.py",
            "bundle_manifest_v2.py",
            "continuity_adapters_v2.py",
            "export_profile_v2.py",
            "handoff_review_v2.py",
        ):
            self.assertTrue((src_root / name).exists(), msg=name)

    def test_qs_v2_milestone_inventory_expected_job_layers_present_in_report_generate(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            result = run_registered_job(
                "qs.report_generate",
                {
                    "run_id": "run_inventory_v2",
                    "project_id": "prj_inventory",
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
            for key in (
                "report_generate",
                "consistency_check",
                "release_pack",
                "bundle_manifest",
                "export_profile",
                "handoff_review",
            ):
                self.assertIn(key, details)

    def test_qs_v2_milestone_inventory_v1_path_unchanged(self) -> None:
        result = run_registered_job(
            "qs.report_export",
            {"run_id": "run_inventory_v1", "project_id": "prj_inventory_v1"},
        )
        self.assertEqual(result["job_type"], "qs.report_generate")
        self.assertIn("artifact_refs", result)
        for key in (
            "consistency_check",
            "release_pack",
            "bundle_manifest",
            "export_profile",
            "handoff_review",
        ):
            self.assertNotIn(key, result["details"])


if __name__ == "__main__":
    unittest.main()
