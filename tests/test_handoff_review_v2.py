from __future__ import annotations

import unittest

from universal_qs_engine.errors import QSJobError
from universal_qs_engine.handoff_review_v2 import build_handoff_review_v2


class HandoffReviewV2Tests(unittest.TestCase):
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

    def _consistency_payload(self) -> dict:
        return {
            "consistency_schema_version": "qs.consistency_check.v2",
            "status": "ok",
        }

    def _release_pack_payload(self) -> dict:
        return {
            "release_pack_schema_version": "qs.release_pack.v2",
            "approval_signals": {
                "requires_po_review": True,
            },
        }

    def _bundle_manifest_payload(self) -> dict:
        return {
            "bundle_manifest_schema_version": "qs.bundle_manifest.v2",
            "components": {
                "report": True,
                "consistency_check": True,
                "release_pack": True,
                "po": True,
            },
            "review_checklist": [{"check_id": "report_ready", "status": "ok"}],
        }

    def _export_profile_payload(self) -> dict:
        return {
            "export_profile_schema_version": "qs.export_profile.v2",
            "deliverables": [{"deliverable_id": "report"}],
            "handoff_summary": {"report_profile_id": "default_qs_v2"},
        }

    def _po_payload(self) -> dict:
        return {
            "vendor": {"vendor_id": "vendor_001"},
            "line_items": [{"item_code": "A1"}],
            "total_cost": 1250.0,
            "currency": "THB",
        }

    def test_success_path_with_full_payload_stack(self) -> None:
        result = build_handoff_review_v2(
            self._report_payload(),
            self._consistency_payload(),
            self._release_pack_payload(),
            self._bundle_manifest_payload(),
            self._export_profile_payload(),
            self._po_payload(),
        )
        self.assertEqual(result["handoff_review_schema_version"], "qs.handoff_review.v2")
        self.assertEqual(result["status"], "ready")
        self.assertTrue(result["headline"]["requires_po_review"])
        self.assertEqual(result["headline"]["po_total_cost"], 1250.0)

    def test_success_path_with_minimal_explicit_v2_stack_and_missing_optional_payloads(self) -> None:
        result = build_handoff_review_v2(self._report_payload())
        self.assertEqual(result["status"], "warning")
        self.assertEqual(result["headline"]["consistency_status"], "warning")
        self.assertIn("warning_count", result["headline"])

    def test_reject_malformed_report_payload(self) -> None:
        with self.assertRaises(QSJobError):
            build_handoff_review_v2({"summary": {}, "sections": []})

    def test_reject_malformed_export_profile_payload(self) -> None:
        with self.assertRaises(QSJobError):
            build_handoff_review_v2(
                self._report_payload(),
                self._consistency_payload(),
                self._release_pack_payload(),
                self._bundle_manifest_payload(),
                {"export_profile_schema_version": "qs.export_profile.v2"},
            )

    def test_deterministic_decision_signals_ordering(self) -> None:
        result = build_handoff_review_v2(self._report_payload())
        self.assertEqual(
            [item["signal_id"] for item in result["decision_signals"]],
            ["consistency_status", "po_review", "bundle_readiness"],
        )

    def test_deterministic_operator_checks_ordering(self) -> None:
        result = build_handoff_review_v2(self._report_payload())
        self.assertEqual(
            [item["check_id"] for item in result["operator_checks"]],
            ["report_ready", "consistency_reviewed", "export_profile_ready"],
        )

    def test_deterministic_warning_ordering(self) -> None:
        first = build_handoff_review_v2(self._report_payload())
        second = build_handoff_review_v2(self._report_payload())
        self.assertEqual(first["warnings"], second["warnings"])
        self.assertEqual(
            [item["code"] for item in first["warnings"]],
            [
                "missing_bundle_manifest_details",
                "missing_consistency_details",
                "missing_export_profile_details",
                "missing_release_pack_details",
            ],
        )


if __name__ == "__main__":
    unittest.main()
