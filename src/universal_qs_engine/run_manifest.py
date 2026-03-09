from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime

from .job_contracts import UnknownJobContractError, get_job_contract

TERMINAL_STATES: frozenset[str] = frozenset({"completed", "failed", "rejected"})
_VALID_TRANSITIONS: dict[str, frozenset[str]] = {
    "submitted": frozenset({"submitted", "queued", "failed", "rejected"}),
    "queued": frozenset({"queued", "running", "failed", "rejected", "blocked_approval"}),
    "running": frozenset({"running", "blocked_approval", "completed", "failed", "rejected"}),
    "blocked_approval": frozenset({"blocked_approval", "queued", "failed", "rejected"}),
    "completed": frozenset({"completed"}),
    "failed": frozenset({"failed"}),
    "rejected": frozenset({"rejected"}),
}


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _build_run_id(job_type: str, project_id: str) -> str:
    job_suffix = job_type.replace("qs.", "").replace(".", "_")
    return f"{project_id}__{job_suffix}"


@dataclass(frozen=True, slots=True)
class ArtifactRecord:
    artifact_type: str
    path: str
    created_at: str

    def to_dict(self) -> dict[str, str]:
        return {
            "artifact_type": self.artifact_type,
            "path": self.path,
            "created_at": self.created_at,
        }


@dataclass(frozen=True, slots=True)
class RunManifest:
    run_id: str
    job_type: str
    project_id: str
    status: str
    requires_approval: bool
    artifacts: tuple[ArtifactRecord, ...]
    started_at: str
    finished_at: str | None


def create_run_manifest(job_type: str, project_id: str) -> RunManifest:
    contract = get_job_contract(job_type)
    started_at = _utc_now()
    return RunManifest(
        run_id=_build_run_id(job_type, project_id),
        job_type=contract.job_type,
        project_id=project_id,
        status="submitted",
        requires_approval=contract.requires_approval,
        artifacts=(),
        started_at=started_at,
        finished_at=None,
    )


def transition_status(manifest: RunManifest, new_status: str) -> RunManifest:
    contract = get_job_contract(manifest.job_type)
    if new_status not in contract.allowed_states:
        raise ValueError(f"invalid_status:{new_status}")
    allowed_next = _VALID_TRANSITIONS.get(manifest.status, frozenset())
    if new_status not in allowed_next:
        raise ValueError(f"invalid_transition:{manifest.status}->{new_status}")

    finished_at = manifest.finished_at
    if new_status in TERMINAL_STATES and finished_at is None:
        finished_at = _utc_now()
    if new_status not in TERMINAL_STATES:
        finished_at = None

    return replace(manifest, status=new_status, finished_at=finished_at)


def attach_artifact(manifest: RunManifest, artifact_type: str, artifact_path: str) -> RunManifest:
    if not artifact_type or not artifact_type.strip():
        raise ValueError("artifact_type_required")
    if not artifact_path or not artifact_path.strip():
        raise ValueError("artifact_path_required")

    created_at = manifest.finished_at or manifest.started_at
    record = ArtifactRecord(
        artifact_type=artifact_type.strip(),
        path=artifact_path.strip(),
        created_at=created_at,
    )
    return replace(manifest, artifacts=manifest.artifacts + (record,))
