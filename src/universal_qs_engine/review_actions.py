from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from .project_store import load_project, save_project
from .review_engine import compute_flag_id, rebuild_review_flags


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ack_review_flag(project_id: str, flag_id: str, comment: str) -> dict[str, Any]:
    project = load_project(project_id)
    resolutions = project.setdefault("review_resolutions", {})
    resolutions[flag_id] = {
        "resolution_kind": "ack_note",
        "comment": comment,
        "timestamp": _utc_now(),
    }
    save_project(project)
    rebuild_review_flags(project_id)
    return resolutions[flag_id]


def override_segment_dim(project_id: str, segment_id: str, field: str, value: float, justification: str, flag_id: str | None = None) -> dict[str, Any]:
    if field not in {"length", "width", "depth"}:
        raise ValueError(field)
    project = load_project(project_id)
    segment = next((item for item in project.get("takeoff", {}).get("segments", []) if item.get("segment_id") == segment_id), None)
    if segment is None:
        raise KeyError(segment_id)

    overrides = segment.setdefault("overrides", {})
    override_notes = segment.setdefault("override_notes", [])
    overrides[field] = float(value)
    override_note = {
        "field": field,
        "value": float(value),
        "justification": justification,
        "timestamp": _utc_now(),
    }
    override_notes.append(override_note)
    segment["dirty"] = True
    segment["basis_status"] = "MANUAL_ALLOWANCE"

    if flag_id:
        resolutions = project.setdefault("review_resolutions", {})
        resolutions[flag_id] = {
            "resolution_kind": "resolve_override",
            "field": field,
            "value": float(value),
            "comment": justification,
            "timestamp": _utc_now(),
        }

    save_project(project)
    rebuild_review_flags(project_id)
    return override_note


def flag_id_for(project_id: str, *, flag_type: str, target_ref: str, message: str, export_rule: str) -> str:
    return compute_flag_id(
        {
            "flag_type": flag_type,
            "target_ref": target_ref,
            "message": message,
            "export_rule": export_rule,
        }
    )
