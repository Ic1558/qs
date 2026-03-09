from __future__ import annotations

import unittest

from universal_qs_engine.bundle_manifest_v2 import build_bundle_manifest_v2
from universal_qs_engine.errors import QSJobError


class BundleManifestV2Tests(unittest.TestCase):
    def _report_payload(self) -> dict:
        return {
            "report_schema_version": "qs.report_generate.v2",
            "report_profile_id": "default_qs_v2",
            "summary": {
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

    def _consistency_payload(self) -> dict:
        return {
            "consistency_schema_version": "qs.consistency_check.v2",
            "status": "ok",
            "checks": {
                "boq_estimate": "ok",
                "estimate_po": "ok",
                "overall": "ok",
            },
            "warnings": [],
        }

    def _release_pack_payload(self) -> dict:
        return {
            "release_pack_schema_version": "qs.release_pack.v2",
            "release_kind": "qs.approval_review_pack",
            "status": "ready",
            "summary": {
                "report_profile_id": "default_qs_v2",
                "estimate_total_cost": 1250.0,
                "po_total_cost": 1250.0,
                "currency": "THB",
            },
            "approval_signals": {
                "requires_po_review": True,
                "consistency_status": "ok",
                "warning_count": 0,
            },
            "sections": [
                {"section_id": "executive_summary", "title": "Executive Summary"},
                {"section_id": "cost_summary", "title": "Cost Summary"},
                {"section_id": "po_summary", "title": "PO Summary"},
                {"section_id": "consistency_review", "title": "Consistency Review"},
            ],
            "warnings": [],
            "source_snapshot": {"report_ref": "inline:report_generate_v2", "po_ref": "inline:po_v2"},
        }

    def _po_payload(self) -> dict:
        return {
            "vendor": {"vendor_id": "vendor_001"},
            "line_items": [{"item_code": "A1"}],
            "total_cost": 1250.0,
            "currency": "THB",
        }

    def test_success_path_with_all_payloads(self) -> None:
        result = build_bundle_manifest_v2(
            self._report_payload(),
            self._consistency_payload(),
            self._release_pack_payload(),
            self._po_payload(),
        )
        self.assertEqual(result["bundle_manifest_schema_version"], "qs.bundle_manifest.v2")
        self.assertEqual(result["status"], "ready")
        self.assertTrue(result["components"]["po"])
        self.assertEqual(result["summary"]["po_total_cost"], 1250.0)

    def test_success_path_without_po_payload(self) -> None:
        release_pack = self._release_pack_payload()
        release_pack["approval_signals"]["requires_po_review"] = False
        result = build_bundle_manifest_v2(
            self._report_payload(),
            self._consistency_payload(),
            release_pack,
        )
        self.assertFalse(result["components"]["po"])
        self.assertNotIn("po_total_cost", result["summary"])

    def test_warning_when_consistency_payload_missing(self) -> None:
        result = build_bundle_manifest_v2(
            self._report_payload(),
            None,
            self._release_pack_payload(),
        )
        self.assertEqual(result["status"], "warning")
        self.assertFalse(result["components"]["consistency_check"])
        self.assertEqual(result["summary"]["consistency_status"], "warning")
        self.assertEqual(result["warnings"][0]["code"], "missing_consistency_details")

    def test_reject_malformed_report_payload(self) -> None:
        with self.assertRaises(QSJobError):
            build_bundle_manifest_v2({"summary": {}, "sections": []})

    def test_reject_malformed_release_pack_payload(self) -> None:
        with self.assertRaises(QSJobError):
            build_bundle_manifest_v2(
                self._report_payload(),
                self._consistency_payload(),
                {"release_pack_schema_version": "qs.release_pack.v2"},
            )

    def test_deterministic_artifact_manifest_ordering(self) -> None:
        result = build_bundle_manifest_v2(
            self._report_payload(),
            self._consistency_payload(),
            self._release_pack_payload(),
            self._po_payload(),
        )
        self.assertEqual(
            result["artifact_manifest"],
            [
                {"artifact_type": "project_qs_report", "logical_role": "report"},
                {"artifact_type": "po_document", "logical_role": "po"},
            ],
        )

    def test_deterministic_review_checklist_ordering(self) -> None:
        result = build_bundle_manifest_v2(
            self._report_payload(),
            self._consistency_payload(),
            self._release_pack_payload(),
            self._po_payload(),
        )
        self.assertEqual(
            [item["check_id"] for item in result["review_checklist"]],
            ["report_present", "consistency_reviewed", "po_review_required"],
        )

    def test_deterministic_warning_ordering(self) -> None:
        first = build_bundle_manifest_v2(self._report_payload())
        second = build_bundle_manifest_v2(self._report_payload())
        self.assertEqual(first["warnings"], second["warnings"])
        self.assertEqual(
            [item["code"] for item in first["warnings"]],
            ["missing_consistency_details", "missing_release_pack_details"],
        )


if __name__ == "__main__":
    unittest.main()
