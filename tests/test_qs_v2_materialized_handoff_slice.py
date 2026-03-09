from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from universal_qs_engine.job_registry import run_registered_job


class QSV2MaterializedHandoffSliceTests(unittest.TestCase):
    def _write_json(self, directory: Path, name: str, payload: dict) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def _build_result(self, root: Path, *, run_id: str, handoff_output_dir: Path | None = None) -> dict:
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
                "project_id": "prj_materialized_handoff",
                "inputs": inputs,
            },
        )

    def test_qs_v2_materialized_handoff_slice_happy_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            out_dir = root / "handoff"
            result = self._build_result(root, run_id="run_materialized_001", handoff_output_dir=out_dir)

            details = result["details"]
            self.assertIn("report_generate", details)
            self.assertIn("consistency_check", details)
            self.assertIn("release_pack", details)
            self.assertIn("bundle_manifest", details)
            self.assertIn("export_profile", details)
            self.assertIn("handoff_review", details)
            self.assertIn("handoff_writer_result", details)

            self.assertTrue((out_dir / "handoff_review.json").exists())
            self.assertTrue((out_dir / "approval_summary.md").exists())
            self.assertTrue((out_dir / "export_profile.json").exists())
            self.assertTrue((out_dir / "bundle_manifest.json").exists())

    def test_qs_v2_materialized_handoff_slice_repeatable_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            first_dir = root / "handoff_one"
            second_dir = root / "handoff_two"

            first = self._build_result(root / "case_one", run_id="run_materialized_repeat", handoff_output_dir=first_dir)
            second = self._build_result(root / "case_two", run_id="run_materialized_repeat", handoff_output_dir=second_dir)

            self.assertEqual(
                first["details"]["handoff_writer_result"]["handoff_writer_schema_version"],
                second["details"]["handoff_writer_result"]["handoff_writer_schema_version"],
            )
            self.assertEqual(
                first["details"]["handoff_writer_result"]["status"],
                second["details"]["handoff_writer_result"]["status"],
            )
            self.assertEqual(
                [item["artifact_type"] for item in first["details"]["handoff_writer_result"]["written_files"]],
                [item["artifact_type"] for item in second["details"]["handoff_writer_result"]["written_files"]],
            )
            self.assertEqual(
                first["details"]["handoff_writer_result"]["warnings"],
                second["details"]["handoff_writer_result"]["warnings"],
            )

            self.assertEqual(
                (first_dir / "approval_summary.md").read_text(encoding="utf-8"),
                (second_dir / "approval_summary.md").read_text(encoding="utf-8"),
            )
            self.assertEqual(
                json.loads((first_dir / "handoff_review.json").read_text(encoding="utf-8")),
                json.loads((second_dir / "handoff_review.json").read_text(encoding="utf-8")),
            )
            self.assertEqual(
                json.loads((first_dir / "export_profile.json").read_text(encoding="utf-8")),
                json.loads((second_dir / "export_profile.json").read_text(encoding="utf-8")),
            )
            self.assertEqual(
                json.loads((first_dir / "bundle_manifest.json").read_text(encoding="utf-8")),
                json.loads((second_dir / "bundle_manifest.json").read_text(encoding="utf-8")),
            )

    def test_qs_v2_materialized_handoff_slice_without_output_dir_skips_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            result = self._build_result(root, run_id="run_materialized_no_write")
            details = result["details"]

            self.assertIn("report_generate", details)
            self.assertIn("consistency_check", details)
            self.assertIn("release_pack", details)
            self.assertIn("bundle_manifest", details)
            self.assertIn("export_profile", details)
            self.assertIn("handoff_review", details)
            self.assertNotIn("handoff_writer_result", details)
            self.assertEqual(set(path.name for path in root.iterdir()), {"boq.json", "estimate.json", "po.json"})

    def test_qs_v2_materialized_handoff_slice_v1_path_unchanged(self) -> None:
        result = run_registered_job(
            "qs.report_export",
            {"run_id": "run_materialized_v1", "project_id": "prj_v1"},
        )
        self.assertEqual(result["job_type"], "qs.report_generate")
        self.assertIn("artifact_refs", result)
        self.assertNotIn("consistency_check", result["details"])
        self.assertNotIn("release_pack", result["details"])
        self.assertNotIn("bundle_manifest", result["details"])
        self.assertNotIn("export_profile", result["details"])
        self.assertNotIn("handoff_review", result["details"])
        self.assertNotIn("handoff_writer_result", result["details"])


if __name__ == "__main__":
    unittest.main()
