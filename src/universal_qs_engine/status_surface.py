from __future__ import annotations

from .run_manifest import RunManifest


def build_status_payload(manifest: RunManifest) -> dict[str, object]:
    return {
        "run_id": manifest.run_id,
        "job_type": manifest.job_type,
        "project_id": manifest.project_id,
        "status": manifest.status,
        "requires_approval": manifest.requires_approval,
        "artifacts": [artifact.to_dict() for artifact in manifest.artifacts],
        "started_at": manifest.started_at,
        "finished_at": manifest.finished_at,
    }
