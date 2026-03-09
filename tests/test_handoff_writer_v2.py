from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from universal_qs_engine.errors import QSJobError
from universal_qs_engine.handoff_writer_v2 import write_handoff_artifacts_v2
from universal_qs_engine.job_registry import run_registered_job


class HandoffWriterV2Tests(unittest.TestCase):
    def _report_payload(self) -> dict:
        return {
            "report_schema_version": "qs.report_generate.v2",
            "report_profile_id": "default_qs_v2",
            "summary": {
                "estimate_total_cost": 1250.0,
                "currency": "THB",
            },
            "sections": ["executive_summary", "cost_summary", "po_summary"],
        }

    def _handoff_review_payload(self) -> dict:
        return {
            "handoff_review_schema_version": "qs.handoff_review.v2",
            "headline": {
                "consistency_status": "ok",
                "warning_count": 0,
                "requires_po_review": True,
                "estimate_total_cost": 1250.0,
                "po_total_cost": 1250.0,
                "currency": "THB",
            },
            "decision_signals": [
                {"signal_id": "consistency_status", "level": "ok", "message": "Consistency status is ok."},
                {"signal_id": "po_review", "level": "warning", "message": "PO review is required."},
                {"signal_id": "bundle_readiness", "level": "ok", "message": "Bundle and export profile are ready."},
            ],
            "operator_checks": [
                {"check_id": "report_ready", "status": "ok"},
                {"check_id": "consistency_reviewed", "status": "ok"},
                {"check_id": "export_profile_ready", "status": "ok"},
            ],
            "warnings": [],
        }

    def _export_profile_payload(self) -> dict:
        return {
            "export_profile_schema_version": "qs.export_profile.v2",
            "deliverables": [
                {"deliverable_id": "report", "artifact_type": "project_qs_report", "required": True, "present": True},
                {"deliverable_id": "po", "artifact_type": "po_document", "required": False, "present": True},
            ],
            "handoff_summary": {
                "report_profile_id": "default_qs_v2",
                "consistency_status": "ok",
                "warning_count": 0,
                "estimate_total_cost": 1250.0,
                "po_total_cost": 1250.0,
                "currency": "THB",
            },
        }

    def _release_pack_payload(self) -> dict:
        return {
            "release_pack_schema_version": "qs.release_pack.v2",
            "approval_signals": {"requires_po_review": True},
        }

    def _bundle_manifest_payload(self) -> dict:
        return {
            "bundle_manifest_schema_version": "qs.bundle_manifest.v2",
            "components": {"report": True, "release_pack": True},
            "review_checklist": [{"check_id": "report_ready", "status": "ok"}],
        }

    def test_success_path_writes_minimum_required_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = write_handoff_artifacts_v2(
                tmpdir,
                report_payload=self._report_payload(),
                handoff_review_payload=self._handoff_review_payload(),
            )
            self.assertEqual(result["status"], "warning")
            paths = {Path(item["path"]).name for item in result["written_files"]}
            self.assertEqual(paths, {"handoff_review.json", "approval_summary.md"})

    def test_success_path_writes_optional_json_files_when_optional_payloads_are_provided(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = write_handoff_artifacts_v2(
                tmpdir,
                report_payload=self._report_payload(),
                handoff_review_payload=self._handoff_review_payload(),
                export_profile_payload=self._export_profile_payload(),
                release_pack_payload=self._release_pack_payload(),
                bundle_manifest_payload=self._bundle_manifest_payload(),
            )
            self.assertEqual(result["status"], "written")
            paths = {Path(item["path"]).name for item in result["written_files"]}
            self.assertEqual(paths, {"handoff_review.json", "export_profile.json", "bundle_manifest.json", "approval_summary.md"})

    def test_markdown_summary_has_deterministic_section_ordering(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            write_handoff_artifacts_v2(
                tmpdir,
                report_payload=self._report_payload(),
                handoff_review_payload=self._handoff_review_payload(),
                export_profile_payload=self._export_profile_payload(),
                release_pack_payload=self._release_pack_payload(),
                bundle_manifest_payload=self._bundle_manifest_payload(),
            )
            content = (Path(tmpdir) / "approval_summary.md").read_text(encoding="utf-8")
            self.assertLess(content.index("# QS Approval Summary"), content.index("## Headline"))
            self.assertLess(content.index("## Headline"), content.index("## Decision Signals"))
            self.assertLess(content.index("## Decision Signals"), content.index("## Operator Checks"))
            self.assertLess(content.index("## Operator Checks"), content.index("## Deliverables"))
            self.assertLess(content.index("## Deliverables"), content.index("## Warnings"))

    def test_missing_optional_payloads_degrade_safely(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = write_handoff_artifacts_v2(
                tmpdir,
                report_payload=self._report_payload(),
                handoff_review_payload=self._handoff_review_payload(),
            )
            self.assertEqual(
                [item["code"] for item in result["warnings"]],
                ["missing_bundle_manifest_details", "missing_export_profile_details", "missing_release_pack_details"],
            )

    def test_malformed_handoff_review_payload_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(QSJobError):
                write_handoff_artifacts_v2(
                    tmpdir,
                    report_payload=self._report_payload(),
                    handoff_review_payload={"handoff_review_schema_version": "qs.handoff_review.v2"},
                )

    def test_writes_are_contained_under_output_dir_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir)
            result = write_handoff_artifacts_v2(
                out_dir,
                report_payload=self._report_payload(),
                handoff_review_payload=self._handoff_review_payload(),
            )
            for item in result["written_files"]:
                path = Path(item["path"]).resolve()
                self.assertTrue(path.is_relative_to(out_dir.resolve()))

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
                    "run_id": "run_handoff_writer",
                    "project_id": "prj_handoff_writer",
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
            self.assertTrue((out_dir / "handoff_review.json").exists())
            self.assertTrue((out_dir / "approval_summary.md").exists())

    def test_v1_compatibility_path_remains_unchanged(self) -> None:
        result = run_registered_job(
            "qs.report_export",
            {"run_id": "run_writer_v1", "project_id": "prj_v1"},
        )
        self.assertNotIn("handoff_writer_result", result["details"])

    def test_explicit_v2_path_without_handoff_output_dir_remains_unchanged_except_no_writing_occurs(self) -> None:
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
                    "run_id": "run_writer_no_output",
                    "project_id": "prj_writer_no_output",
                    "inputs": {
                        "boq_ref": str(boq),
                        "estimate_ref": str(estimate),
                        "po_ref": str(po),
                        "report_profile_id": "default_qs_v2",
                    },
                },
            )
            self.assertNotIn("handoff_writer_result", result["details"])
            self.assertEqual(set(root.glob("*.json")), {boq, estimate, po})

    def _write_json(self, directory: Path, name: str, payload: dict) -> Path:
        path = directory / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path


if __name__ == "__main__":
    unittest.main()
