from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from universal_qs_engine.job_registry import run_registered_job


class QSV2ReleaseCandidateTests(unittest.TestCase):
    def _repo_root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    def _write_json(self, directory: Path, name: str, payload: dict) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def _explicit_v2_result(self, root: Path, *, run_id: str, handoff_output_dir: Path | None = None) -> dict:
        boq = self._write_json(
            root,
            "boq.json",
            {"items": [{"item_code": "paint", "quantity": 5, "unit": "m2"}]},
        )
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
        inputs = {
            "boq_ref": str(boq),
            "estimate_ref": str(estimate),
            "po_ref": str(po),
            "report_profile_id": "default_qs_v2",
        }
        if handoff_output_dir is not None:
            inputs["handoff_output_dir"] = str(handoff_output_dir)
        return run_registered_job(
            "qs.report_generate",
            {
                "run_id": run_id,
                "project_id": "prj_qs_rc",
                "inputs": inputs,
            },
        )

    def test_qs_v2_release_candidate_expected_review_docs_exist(self) -> None:
        review_root = self._repo_root() / "review"
        for name in (
            "QS_V2_VERTICAL_SLICE_SEAL.md",
            "QS_V2_OPERATOR_PREP_SLICE_SEAL.md",
            "QS_V2_MILESTONE_CLOSEOUT.md",
            "QS_V2_MATERIALIZED_HANDOFF_SLICE_SEAL.md",
            "QS_V2_RELEASE_CANDIDATE.md",
        ):
            self.assertTrue((review_root / name).exists(), msg=name)

    def test_qs_v2_release_candidate_explicit_v2_report_stack_complete(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            result = self._explicit_v2_result(root, run_id="run_qs_rc_stack")
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
            self.assertNotIn("handoff_writer_result", details)

            output_result = self._explicit_v2_result(
                root / "with_output",
                run_id="run_qs_rc_stack_write",
                handoff_output_dir=root / "handoff",
            )
            self.assertIn("handoff_writer_result", output_result["details"])

    def test_qs_v2_release_candidate_materialized_outputs_stable(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            first_dir = root / "handoff_one"
            second_dir = root / "handoff_two"
            self._explicit_v2_result(root / "case_one", run_id="run_qs_rc_repeat", handoff_output_dir=first_dir)
            self._explicit_v2_result(root / "case_two", run_id="run_qs_rc_repeat", handoff_output_dir=second_dir)

            for name in ("handoff_review.json", "approval_summary.md", "export_profile.json", "bundle_manifest.json"):
                first_content = (first_dir / name).read_text(encoding="utf-8")
                second_content = (second_dir / name).read_text(encoding="utf-8")
                self.assertEqual(first_content, second_content, msg=name)

    def test_qs_v2_release_candidate_v1_path_unchanged(self) -> None:
        result = run_registered_job(
            "qs.report_export",
            {"run_id": "run_qs_rc_v1", "project_id": "prj_qs_rc_v1"},
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
        ):
            self.assertNotIn(key, result["details"])


if __name__ == "__main__":
    unittest.main()
