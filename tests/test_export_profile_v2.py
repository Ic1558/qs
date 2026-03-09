from __future__ import annotations

import unittest

from universal_qs_engine.errors import QSJobError
from universal_qs_engine.export_profile_v2 import build_export_profile_v2


class ExportProfileV2Tests(unittest.TestCase):
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
            "review_checklist": [
                {"check_id": "report_present", "status": "ok"},
            ],
        }

    def _po_payload(self) -> dict:
        return {
            "vendor": {"vendor_id": "vendor_001"},
            "line_items": [{"item_code": "A1"}],
            "total_cost": 1250.0,
            "currency": "THB",
        }

    def test_success_path_with_full_payload_stack(self) -> None:
        result = build_export_profile_v2(
            self._report_payload(),
            self._consistency_payload(),
            self._release_pack_payload(),
            self._bundle_manifest_payload(),
            self._po_payload(),
        )
        self.assertEqual(result["export_profile_schema_version"], "qs.export_profile.v2")
        self.assertEqual(result["status"], "ready")
        self.assertTrue(result["deliverables"][1]["present"])
        self.assertEqual(result["handoff_summary"]["po_total_cost"], 1250.0)

    def test_success_path_with_report_only_minimal_v2_payload_stack(self) -> None:
        result = build_export_profile_v2(self._report_payload())
        self.assertEqual(result["status"], "warning")
        self.assertFalse(result["deliverables"][1]["present"])
        self.assertNotIn("po_total_cost", result["handoff_summary"])

    def test_reject_malformed_report_payload(self) -> None:
        with self.assertRaises(QSJobError):
            build_export_profile_v2({"summary": {}, "sections": []})

    def test_reject_malformed_bundle_manifest_payload(self) -> None:
        with self.assertRaises(QSJobError):
            build_export_profile_v2(
                self._report_payload(),
                self._consistency_payload(),
                self._release_pack_payload(),
                {"bundle_manifest_schema_version": "qs.bundle_manifest.v2"},
            )

    def test_deterministic_deliverables_ordering(self) -> None:
        result = build_export_profile_v2(
            self._report_payload(),
            self._consistency_payload(),
            self._release_pack_payload(),
            self._bundle_manifest_payload(),
            self._po_payload(),
        )
        self.assertEqual(
            result["deliverables"],
            [
                {
                    "deliverable_id": "report",
                    "artifact_type": "project_qs_report",
                    "required": True,
                    "present": True,
                },
                {
                    "deliverable_id": "po",
                    "artifact_type": "po_document",
                    "required": False,
                    "present": True,
                },
            ],
        )

    def test_deterministic_review_targets_ordering(self) -> None:
        result = build_export_profile_v2(self._report_payload())
        self.assertEqual(
            result["review_targets"],
            [
                {"target_id": "cost_summary", "source": "report"},
                {"target_id": "consistency_review", "source": "consistency_check"},
                {"target_id": "approval_pack", "source": "release_pack"},
            ],
        )

    def test_deterministic_warning_ordering(self) -> None:
        first = build_export_profile_v2(self._report_payload())
        second = build_export_profile_v2(self._report_payload())
        self.assertEqual(first["warnings"], second["warnings"])
        self.assertEqual(
            [item["code"] for item in first["warnings"]],
            [
                "missing_bundle_manifest_details",
                "missing_consistency_details",
                "missing_release_pack_details",
            ],
        )


if __name__ == "__main__":
    unittest.main()
