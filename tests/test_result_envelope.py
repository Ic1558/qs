from __future__ import annotations

import unittest
from dataclasses import replace

from universal_qs_engine.run_manifest import ArtifactRecord, attach_artifact, create_run_manifest, transition_status
from universal_qs_engine.result_envelope import ResultEnvelopeError, build_result_envelope


class ResultEnvelopeTests(unittest.TestCase):
    def test_successful_envelope_creation_from_completed_manifest(self) -> None:
        manifest = create_run_manifest("qs.boq_generate", "prj_201")
        manifest = transition_status(manifest, "queued")
        manifest = transition_status(manifest, "running")
        manifest = transition_status(manifest, "completed")
        manifest = attach_artifact(manifest, "boq_json", "outputs/prj_201/boq.json")
        manifest = attach_artifact(manifest, "run_manifest", "outputs/prj_201/run_manifest.json")

        envelope = build_result_envelope(
            manifest,
            expected_outputs=("boq_json", "internal_trace_xlsx", "run_manifest"),
        )

        self.assertEqual(envelope.status, "completed")
        self.assertEqual(envelope.outcome_classification, "success")
        self.assertIsNone(envelope.error_code)
        self.assertEqual(
            [artifact.to_dict() for artifact in envelope.artifact_refs],
            [
                {
                    "artifact_type": "boq_json",
                    "path": "outputs/prj_201/boq.json",
                    "created_at": manifest.finished_at,
                },
                {
                    "artifact_type": "run_manifest",
                    "path": "outputs/prj_201/run_manifest.json",
                    "created_at": manifest.finished_at,
                },
            ],
        )

    def test_failed_envelope_creation_from_failed_manifest(self) -> None:
        manifest = create_run_manifest("qs.compliance_check", "prj_202")
        manifest = transition_status(manifest, "queued")
        manifest = transition_status(manifest, "running")
        manifest = transition_status(manifest, "failed")

        envelope = build_result_envelope(
            manifest,
            expected_outputs=("compliance_report_json", "gate_summary", "run_manifest"),
            error_code="compliance_failed",
            error_message="Compliance evaluation failed deterministically",
        )

        self.assertEqual(envelope.status, "failed")
        self.assertEqual(envelope.outcome_classification, "failure")
        self.assertEqual(envelope.error_code, "compliance_failed")
        self.assertEqual(envelope.status_payload["status"], "failed")

    def test_rejection_on_missing_required_fields(self) -> None:
        manifest = create_run_manifest("qs.report_export", "prj_203")
        manifest = transition_status(manifest, "queued")
        manifest = transition_status(manifest, "running")
        manifest = transition_status(manifest, "completed")
        broken = replace(manifest, run_id="")

        with self.assertRaises(ResultEnvelopeError):
            build_result_envelope(
                broken,
                expected_outputs=("summary_report", "export_bundle", "run_manifest"),
            )

    def test_rejection_on_malformed_artifact_data(self) -> None:
        manifest = create_run_manifest("qs.po_generate", "prj_204")
        manifest = transition_status(manifest, "queued")
        manifest = transition_status(manifest, "running")
        manifest = transition_status(manifest, "failed")
        broken = replace(
            manifest,
            artifacts=(ArtifactRecord(artifact_type="", path="outputs/prj_204/po.json", created_at=manifest.finished_at or ""),),
        )

        with self.assertRaises(ResultEnvelopeError):
            build_result_envelope(
                broken,
                expected_outputs=("po_package", "po_manifest", "run_manifest"),
                error_code="po_failed",
                error_message="PO generation failed",
            )

    def test_deterministic_dict_output_and_artifact_ordering(self) -> None:
        manifest = create_run_manifest("qs.boq_generate", "prj_205")
        manifest = transition_status(manifest, "queued")
        manifest = transition_status(manifest, "running")
        manifest = transition_status(manifest, "completed")
        manifest = attach_artifact(manifest, "internal_trace_xlsx", "outputs/prj_205/trace.xlsx")
        manifest = attach_artifact(manifest, "boq_json", "outputs/prj_205/boq.json")

        envelope_a = build_result_envelope(
            manifest,
            expected_outputs=("boq_json", "internal_trace_xlsx", "run_manifest"),
        )
        envelope_b = build_result_envelope(
            manifest,
            expected_outputs=("boq_json", "internal_trace_xlsx", "run_manifest"),
        )

        self.assertEqual(envelope_a.to_dict(), envelope_b.to_dict())
        self.assertEqual(
            [artifact["artifact_type"] for artifact in envelope_a.to_dict()["artifact_refs"]],
            ["internal_trace_xlsx", "boq_json"],
        )

    def test_source_manifest_is_not_mutated(self) -> None:
        manifest = create_run_manifest("qs.compliance_check", "prj_206")
        manifest = transition_status(manifest, "queued")
        manifest = transition_status(manifest, "running")
        manifest = transition_status(manifest, "failed")
        before = manifest.artifacts

        build_result_envelope(
            manifest,
            expected_outputs=("compliance_report_json", "gate_summary", "run_manifest"),
            error_code="compliance_failed",
            error_message="Compliance failed",
        )

        self.assertEqual(manifest.artifacts, before)
        self.assertEqual(manifest.status, "failed")

    def test_status_surface_consistency_and_non_terminal_rejection(self) -> None:
        manifest = create_run_manifest("qs.report_export", "prj_207")
        manifest = transition_status(manifest, "queued")

        with self.assertRaises(ResultEnvelopeError):
            build_result_envelope(
                manifest,
                expected_outputs=("summary_report", "export_bundle", "run_manifest"),
            )

        terminal = transition_status(manifest, "running")
        terminal = transition_status(terminal, "rejected")
        envelope = build_result_envelope(
            terminal,
            expected_outputs=("summary_report", "export_bundle", "run_manifest"),
            error_code="run_rejected",
            error_message="Report export was rejected",
        )
        self.assertEqual(envelope.status_payload["status"], terminal.status)
        self.assertTrue(envelope.proof_flags["status_surface_consistent"])


if __name__ == "__main__":
    unittest.main()
