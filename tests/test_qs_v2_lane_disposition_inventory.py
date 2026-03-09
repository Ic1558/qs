from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from universal_qs_engine.job_registry import run_registered_job


class QSV2LaneDispositionInventoryTests(unittest.TestCase):
    def _repo_root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    def _write_json(self, directory: Path, name: str, payload: dict) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_qs_v2_lane_disposition_required_review_docs_exist(self) -> None:
        review_root = self._repo_root() / "review"
        for name in (
            "QS_V2_VERTICAL_SLICE_SEAL.md",
            "QS_V2_OPERATOR_PREP_SLICE_SEAL.md",
            "QS_V2_MILESTONE_CLOSEOUT.md",
            "QS_V2_MATERIALIZED_HANDOFF_SLICE_SEAL.md",
            "QS_V2_RELEASE_CANDIDATE.md",
            "QS_V2_EXPORT_PACKAGE_SLICE_SEAL.md",
            "QS_V2_LANE_DISPOSITION.md",
        ):
            self.assertTrue((review_root / name).exists(), msg=name)

    def test_qs_v2_lane_disposition_v2_stack_still_complete(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            out_dir = root / "handoff"
            result = run_registered_job(
                "qs.report_generate",
                {
                    "run_id": "run_lane_disposition_v2",
                    "project_id": "prj_lane_disposition",
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
                        "handoff_output_dir": str(out_dir),
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
                "handoff_writer_result",
                "export_package_index",
            ):
                self.assertIn(key, details)

    def test_qs_v2_lane_disposition_v1_path_unchanged(self) -> None:
        result = run_registered_job(
            "qs.report_export",
            {"run_id": "run_lane_disposition_v1", "project_id": "prj_lane_disposition_v1"},
        )
        self.assertEqual(result["job_type"], "qs.report_generate")
        self.assertIn("artifact_refs", result)
        for key in (
            "consistency_check",
            "release_pack",
            "bundle_manifest",
            "export_profile",
            "handoff_review",
            "handoff_writer_result",
            "export_package_index",
        ):
            self.assertNotIn(key, result["details"])


if __name__ == "__main__":
    unittest.main()
