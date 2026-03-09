from __future__ import annotations

from dataclasses import dataclass

from .run_manifest import ArtifactRecord, RunManifest, TERMINAL_STATES
from .status_surface import build_status_payload


class ResultEnvelopeError(ValueError):
    """Raised when a manifest cannot be projected into a terminal result envelope."""


@dataclass(frozen=True, slots=True)
class ResultEnvelope:
    run_id: str
    job_type: str
    project_id: str
    status: str
    requires_approval: bool
    expected_outputs: tuple[str, ...]
    artifact_refs: tuple[ArtifactRecord, ...]
    error_code: str | None
    error_message: str | None
    outcome_classification: str
    outcome_summary: str
    proof_flags: dict[str, bool]
    manifest_payload: dict[str, object]
    status_payload: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "job_type": self.job_type,
            "project_id": self.project_id,
            "status": self.status,
            "requires_approval": self.requires_approval,
            "expected_outputs": list(self.expected_outputs),
            "artifact_refs": [artifact.to_dict() for artifact in self.artifact_refs],
            "error_code": self.error_code,
            "error_message": self.error_message,
            "outcome_classification": self.outcome_classification,
            "outcome_summary": self.outcome_summary,
            "proof_flags": dict(self.proof_flags),
            "manifest_payload": dict(self.manifest_payload),
            "status_payload": dict(self.status_payload),
        }


def _validate_manifest(manifest: RunManifest) -> None:
    if not manifest.run_id or not manifest.run_id.strip():
        raise ResultEnvelopeError("run_id_required")
    if not manifest.job_type or not manifest.job_type.strip():
        raise ResultEnvelopeError("job_type_required")
    if not manifest.project_id or not manifest.project_id.strip():
        raise ResultEnvelopeError("project_id_required")
    if not manifest.status or not manifest.status.strip():
        raise ResultEnvelopeError("status_required")
    if manifest.status not in TERMINAL_STATES:
        raise ResultEnvelopeError(f"terminal_status_required:{manifest.status}")
    if not manifest.started_at or not manifest.started_at.strip():
        raise ResultEnvelopeError("started_at_required")
    if not manifest.finished_at or not manifest.finished_at.strip():
        raise ResultEnvelopeError("finished_at_required")
    if not isinstance(manifest.artifacts, tuple):
        raise ResultEnvelopeError("artifacts_tuple_required")
    for index, artifact in enumerate(manifest.artifacts):
        if not isinstance(artifact, ArtifactRecord):
            raise ResultEnvelopeError(f"artifact_invalid_type:{index}")
        if not artifact.artifact_type or not artifact.artifact_type.strip():
            raise ResultEnvelopeError(f"artifact_type_required:{index}")
        if not artifact.path or not artifact.path.strip():
            raise ResultEnvelopeError(f"artifact_path_required:{index}")
        if not artifact.created_at or not artifact.created_at.strip():
            raise ResultEnvelopeError(f"artifact_created_at_required:{index}")


def _classify_outcome(status: str) -> tuple[str, str | None]:
    if status == "completed":
        return "success", None
    if status == "failed":
        return "failure", "run_failed"
    if status == "rejected":
        return "rejection", "run_rejected"
    raise ResultEnvelopeError(f"unsupported_terminal_status:{status}")


def _build_outcome_summary(status: str, project_id: str, job_type: str) -> str:
    if status == "completed":
        return f"{job_type} completed for {project_id}"
    if status == "failed":
        return f"{job_type} failed for {project_id}"
    return f"{job_type} rejected for {project_id}"


def build_result_envelope(
    manifest: RunManifest,
    *,
    expected_outputs: tuple[str, ...],
    error_code: str | None = None,
    error_message: str | None = None,
) -> ResultEnvelope:
    _validate_manifest(manifest)
    if not isinstance(expected_outputs, tuple) or not expected_outputs:
        raise ResultEnvelopeError("expected_outputs_required")
    if any((not output or not output.strip()) for output in expected_outputs):
        raise ResultEnvelopeError("expected_output_invalid")
    if (error_code is None) != (error_message is None):
        raise ResultEnvelopeError("error_fields_must_pair")

    outcome_classification, default_error_code = _classify_outcome(manifest.status)
    if manifest.status == "completed" and (error_code is not None or error_message is not None):
        raise ResultEnvelopeError("success_envelope_cannot_include_error")
    if manifest.status in {"failed", "rejected"}:
        error_code = error_code or default_error_code
        error_message = error_message or _build_outcome_summary(manifest.status, manifest.project_id, manifest.job_type)

    status_payload = build_status_payload(manifest)
    if status_payload["status"] != manifest.status:
        raise ResultEnvelopeError("status_surface_mismatch")

    manifest_payload = {
        "run_id": manifest.run_id,
        "job_type": manifest.job_type,
        "project_id": manifest.project_id,
        "status": manifest.status,
        "requires_approval": manifest.requires_approval,
        "artifacts": [artifact.to_dict() for artifact in manifest.artifacts],
        "started_at": manifest.started_at,
        "finished_at": manifest.finished_at,
    }

    return ResultEnvelope(
        run_id=manifest.run_id,
        job_type=manifest.job_type,
        project_id=manifest.project_id,
        status=manifest.status,
        requires_approval=manifest.requires_approval,
        expected_outputs=expected_outputs,
        artifact_refs=manifest.artifacts,
        error_code=error_code,
        error_message=error_message,
        outcome_classification=outcome_classification,
        outcome_summary=_build_outcome_summary(manifest.status, manifest.project_id, manifest.job_type),
        proof_flags={
            "is_terminal": True,
            "has_finished_at": True,
            "status_surface_consistent": True,
            "artifacts_present": bool(manifest.artifacts),
        },
        manifest_payload=manifest_payload,
        status_payload=status_payload,
    )
