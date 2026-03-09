from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from universal_qs_engine.errors import QSJobError
from universal_qs_engine.release_pack_v2 import build_release_pack_v2


class ReleasePackV2Tests(unittest.TestCase):
    def _write_json(self, directory: Path, name: str, payload: dict) -> Path:
        path = directory / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def _report_doc(self, *, include_consistency: bool = True) -> dict:
        payload = {
            "report_generate": {
                "report_schema_version": "qs.report_generate.v2",
                "report_profile_id": "default_qs_v2",
                "summary": {
                    "project_id": "PRJ_001",
                    "estimate_total_cost": 1250.0,
                    "currency": "THB",
                },
                "sections": [
                    "executive_summary",
                    "boq_summary",
                    "cost_summary",
                    "po_summary",
                ],
            }
        }
        if include_consistency:
            payload["consistency_check"] = {
                "status": "ok",
                "warnings": [],
            }
        return payload

    def test_success_path_with_valid_report_and_po_refs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            report = self._write_json(root, "report.json", self._report_doc())
            po = self._write_json(
                root,
                "po.json",
                {
                    "vendor": {"vendor_id": "vendor_001"},
                    "line_items": [{"item_code": "A1"}],
                    "total_cost": 1250.0,
                    "currency": "THB",
                },
            )
            result = build_release_pack_v2(str(report), str(po))
            self.assertEqual(result["release_pack_schema_version"], "qs.release_pack.v2")
            self.assertEqual(result["status"], "ready")
            self.assertEqual(result["summary"]["project_id"], "PRJ_001")
            self.assertEqual(result["summary"]["po_total_cost"], 1250.0)
            self.assertTrue(result["approval_signals"]["requires_po_review"])

    def test_success_path_with_report_only_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            report = self._write_json(root, "report.json", self._report_doc())
            result = build_release_pack_v2(str(report))
            self.assertEqual(result["status"], "ready")
            self.assertNotIn("po_total_cost", result["summary"])
            self.assertFalse(result["approval_signals"]["requires_po_review"])

    def test_reject_non_json_refs(self) -> None:
        with self.assertRaises(QSJobError):
            build_release_pack_v2("/tmp/report.md", "/tmp/po.json")

    def test_reject_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            report = self._write_json(root, "report.json", self._report_doc())
            with self.assertRaises(QSJobError):
                build_release_pack_v2(str(report), str(root / "missing_po.json"))

    def test_reject_malformed_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            report = root / "report.json"
            report.write_text("{bad", encoding="utf-8")
            with self.assertRaises(QSJobError):
                build_release_pack_v2(str(report))

    def test_reject_malformed_report_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            report = self._write_json(root, "report.json", {"summary": {}, "sections": []})
            with self.assertRaises(QSJobError):
                build_release_pack_v2(str(report))

    def test_deterministic_section_ordering(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            report = self._write_json(root, "report.json", self._report_doc())
            result = build_release_pack_v2(str(report))
            self.assertEqual(
                [section["section_id"] for section in result["sections"]],
                [
                    "executive_summary",
                    "cost_summary",
                    "po_summary",
                    "consistency_review",
                ],
            )

    def test_deterministic_warning_ordering(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            report = self._write_json(root, "report.json", self._report_doc(include_consistency=False))
            first = build_release_pack_v2(str(report))
            second = build_release_pack_v2(str(report))
            self.assertEqual(first["warnings"], second["warnings"])
            self.assertEqual(first["warnings"][0]["code"], "missing_consistency_details")


if __name__ == "__main__":
    unittest.main()
