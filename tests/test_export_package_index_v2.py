from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from universal_qs_engine.export_package_index_v2 import build_export_package_index_v2
from universal_qs_engine.job_registry import run_registered_job


class ExportPackageIndexV2Tests(unittest.TestCase):
    def _write_file(self, directory: Path, name: str, content: str) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / name
        path.write_text(content, encoding="utf-8")
        return path

    def _written_files(self, root: Path, names: list[tuple[str, str]]) -> list[dict[str, str]]:
        output: list[dict[str, str]] = []
        for artifact_type, filename in names:
            path = self._write_file(root, filename, "{}\n" if filename.endswith(".json") else "# summary\n")
            output.append({"artifact_type": artifact_type, "path": str(path)})
        return output

    def _write_json(self, directory: Path, name: str, payload: dict) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_success_path_indexes_required_written_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            written_files = self._written_files(
                root,
                [
                    ("handoff_review", "handoff_review.json"),
                    ("approval_summary", "approval_summary.md"),
                    ("export_profile", "export_profile.json"),
                    ("bundle_manifest", "bundle_manifest.json"),
                ],
            )
            result = build_export_package_index_v2(root, written_files)
            self.assertEqual(result["status"], "ready")
            self.assertTrue(result["summary"]["required_present"])
            self.assertEqual(result["summary"]["file_count"], 4)

    def test_optional_files_may_be_absent_deterministically(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            written_files = self._written_files(
                root,
                [
                    ("handoff_review", "handoff_review.json"),
                    ("approval_summary", "approval_summary.md"),
                ],
            )
            result = build_export_package_index_v2(root, written_files)
            present_map = {item["artifact_type"]: item["present"] for item in result["items"]}
            self.assertTrue(present_map["handoff_review"])
            self.assertTrue(present_map["approval_summary"])
            self.assertFalse(present_map["export_profile"])
            self.assertFalse(present_map["bundle_manifest"])

    def test_missing_required_file_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            written_files = self._written_files(
                root,
                [("handoff_review", "handoff_review.json")],
            )
            result = build_export_package_index_v2(root, written_files)
            self.assertEqual(result["status"], "warning")
            self.assertFalse(result["summary"]["required_present"])
            self.assertEqual([item["code"] for item in result["warnings"]], ["missing_required_file"])

    def test_deterministic_items_ordering(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            written_files = self._written_files(
                root,
                [
                    ("bundle_manifest", "bundle_manifest.json"),
                    ("handoff_review", "handoff_review.json"),
                    ("approval_summary", "approval_summary.md"),
                    ("export_profile", "export_profile.json"),
                ],
            )
            result = build_export_package_index_v2(root, written_files)
            self.assertEqual(
                [item["filename"] for item in result["items"]],
                [
                    "approval_summary.md",
                    "bundle_manifest.json",
                    "export_profile.json",
                    "handoff_review.json",
                ],
            )

    def test_deterministic_warnings_ordering(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            written_files: list[dict[str, str]] = []
            result = build_export_package_index_v2(root, written_files)
            self.assertEqual(
                [item["code"] for item in result["warnings"]],
                ["missing_required_file", "missing_required_file"],
            )

    def test_integration_into_explicit_v2_qs_report_generate_when_handoff_output_dir_is_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            out_dir = root / "handoff"
            boq = self._write_json(root, "boq.json", {"items": []})
            estimate = self._write_json(
                root,
                "estimate.json",
                {"estimate_id": "estimate_001", "line_items": [], "total_cost": 0, "currency": "THB"},
            )
            po = self._write_json(
                root,
                "po.json",
                {"vendor": {"vendor_id": "vendor_001"}, "line_items": [], "total_cost": 0, "currency": "THB"},
            )
            result = run_registered_job(
                "qs.report_generate",
                {
                    "run_id": "run_export_index",
                    "project_id": "prj_export_index",
                    "inputs": {
                        "boq_ref": str(boq),
                        "estimate_ref": str(estimate),
                        "po_ref": str(po),
                        "report_profile_id": "default_qs_v2",
                        "handoff_output_dir": str(out_dir),
                    },
                },
            )
            self.assertIn("handoff_writer_result", result["details"])
            self.assertIn("export_package_index", result["details"])
            self.assertEqual(
                result["details"]["export_package_index"]["export_package_index_schema_version"],
                "qs.export_package_index.v2",
            )

    def test_explicit_v2_without_output_dir_skips_package_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            boq = self._write_json(root, "boq.json", {"items": []})
            estimate = self._write_json(
                root,
                "estimate.json",
                {"estimate_id": "estimate_001", "line_items": [], "total_cost": 0, "currency": "THB"},
            )
            po = self._write_json(
                root,
                "po.json",
                {"vendor": {"vendor_id": "vendor_001"}, "line_items": [], "total_cost": 0, "currency": "THB"},
            )
            result = run_registered_job(
                "qs.report_generate",
                {
                    "run_id": "run_export_index_skip",
                    "project_id": "prj_export_index_skip",
                    "inputs": {
                        "boq_ref": str(boq),
                        "estimate_ref": str(estimate),
                        "po_ref": str(po),
                        "report_profile_id": "default_qs_v2",
                    },
                },
            )
            self.assertNotIn("handoff_writer_result", result["details"])
            self.assertNotIn("export_package_index", result["details"])

    def test_v1_path_remains_unchanged(self) -> None:
        result = run_registered_job(
            "qs.report_export",
            {"run_id": "run_export_index_v1", "project_id": "prj_export_index_v1"},
        )
        self.assertNotIn("handoff_writer_result", result["details"])
        self.assertNotIn("export_package_index", result["details"])


if __name__ == "__main__":
    unittest.main()
