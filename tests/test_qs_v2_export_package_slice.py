from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from universal_qs_engine.job_registry import run_registered_job


class QSV2ExportPackageSliceTests(unittest.TestCase):
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
                "project_id": "prj_export_package",
                "inputs": inputs,
            },
        )

    def test_qs_v2_export_package_slice_happy_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            out_dir = root / "handoff"
            result = self._build_result(root, run_id="run_export_package_001", handoff_output_dir=out_dir)
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

            self.assertTrue((out_dir / "handoff_review.json").exists())
            self.assertTrue((out_dir / "approval_summary.md").exists())
            self.assertTrue((out_dir / "export_profile.json").exists())
            self.assertTrue((out_dir / "bundle_manifest.json").exists())

            index = details["export_package_index"]
            expected_presence = {
                "handoff_review": True,
                "approval_summary": True,
                "export_profile": True,
                "bundle_manifest": True,
            }
            self.assertEqual(
                {item["artifact_type"]: item["present"] for item in index["items"]},
                expected_presence,
            )
            self.assertEqual(index["summary"]["file_count"], 4)
            self.assertTrue(index["summary"]["required_present"])

    def test_qs_v2_export_package_slice_repeatable_index_and_contents(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            first_dir = root / "handoff_one"
            second_dir = root / "handoff_two"

            first = self._build_result(root / "case_one", run_id="run_export_package_repeat", handoff_output_dir=first_dir)
            second = self._build_result(root / "case_two", run_id="run_export_package_repeat", handoff_output_dir=second_dir)

            first_index = first["details"]["export_package_index"]
            second_index = second["details"]["export_package_index"]
            self.assertEqual(first_index["export_package_index_schema_version"], second_index["export_package_index_schema_version"])
            self.assertEqual(first_index["package_kind"], second_index["package_kind"])
            self.assertEqual(first_index["status"], second_index["status"])
            self.assertEqual(first_index["items"], second_index["items"])
            self.assertEqual(first_index["summary"], second_index["summary"])
            self.assertEqual(first_index["warnings"], second_index["warnings"])

            for name in ("handoff_review.json", "approval_summary.md", "export_profile.json", "bundle_manifest.json"):
                self.assertEqual(
                    (first_dir / name).read_text(encoding="utf-8"),
                    (second_dir / name).read_text(encoding="utf-8"),
                )

    def test_qs_v2_export_package_slice_without_output_dir_skips_write_and_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            result = self._build_result(root, run_id="run_export_package_no_output")
            details = result["details"]

            self.assertIn("report_generate", details)
            self.assertIn("consistency_check", details)
            self.assertIn("release_pack", details)
            self.assertIn("bundle_manifest", details)
            self.assertIn("export_profile", details)
            self.assertIn("handoff_review", details)
            self.assertNotIn("handoff_writer_result", details)
            self.assertNotIn("export_package_index", details)

    def test_qs_v2_export_package_slice_v1_path_unchanged(self) -> None:
        result = run_registered_job(
            "qs.report_export",
            {"run_id": "run_export_package_v1", "project_id": "prj_v1"},
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
