from __future__ import annotations

from typing import Any


class QSJobError(ValueError):
    """Raised when a job context is invalid."""


def require_context_value(context: dict[str, Any], key: str) -> str:
    value = str(context.get(key) or "").strip()
    if not value:
        raise QSJobError(f"missing_context:{key}")
    return value


def artifact_ref(run_id: str, folder: str, filename: str, artifact_type: str) -> dict[str, str]:
    return {
        "artifact_type": artifact_type,
        "path": f"artifacts/{folder}/{run_id}/{filename}",
    }
