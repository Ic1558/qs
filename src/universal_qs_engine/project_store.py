from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from .artifacts import DEFAULT_OUTPUT_DIR
from .domain_policy import DEFAULT_CALCULATION_POLICY


PROJECTS_DIR = DEFAULT_OUTPUT_DIR / "projects"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _project_path(project_id: str) -> Path:
    return PROJECTS_DIR / project_id / "project.json"


def ensure_store() -> None:
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)


def default_project_state(payload: Dict[str, Any]) -> Dict[str, Any]:
    project_id = payload.get("project_id") or f"prj_{uuid.uuid4().hex[:10]}"
    now = _utc_now()
    return {
        "project_id": project_id,
        "project": {
            "name": payload.get("name", "Untitled QS Project"),
            "client": payload.get("client", ""),
            "site": payload.get("site", ""),
            "project_type": payload.get("project_type", "main"),
            "factor_mode": payload.get("factor_mode", "private"),
            "overhead_rate": float(payload.get("overhead_rate", 0.12)),
            "vat_enabled": bool(payload.get("vat_enabled", False)),
            "currency": payload.get("currency", "THB"),
            "notes": payload.get("notes", ""),
            "compare_revision": payload.get("compare_revision", {}),
            "calculation_policy": {
                **DEFAULT_CALCULATION_POLICY,
                "overlap_owner": payload.get("overlap_owner", DEFAULT_CALCULATION_POLICY["overlap_owner"]),
            },
        },
        "sources": [],
        "rates": [],
        "takeoff": {
            "members": [],
            "segments": [],
            "components": [],
        },
        "candidates": {
            "components": [],
        },
        "calc_graph": {
            "rows": [],
            "boq_lines": [],
            "last_rebuild_at": None,
            "dirty_all": False,
        },
        "review_flags": [],
        "review_resolutions": {},
        "exports": [],
        "created_at": now,
        "updated_at": now,
    }


def save_project(project: Dict[str, Any]) -> Dict[str, Any]:
    ensure_store()
    project["updated_at"] = _utc_now()
    path = _project_path(project["project_id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8")
    return project


def create_project(payload: Dict[str, Any]) -> Dict[str, Any]:
    project = default_project_state(payload)
    return save_project(project)


def load_project(project_id: str) -> Dict[str, Any]:
    path = _project_path(project_id)
    if not path.exists():
        raise FileNotFoundError(project_id)
    return json.loads(path.read_text(encoding="utf-8"))


def update_project(project_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
    project = load_project(project_id)
    project_fields = project["project"]
    for key, value in patch.items():
        if key in {"compare_revision", "calculation_policy"} and isinstance(value, dict):
            project_fields.setdefault(key, {}).update(value)
        elif key in project_fields:
            project_fields[key] = value
    return save_project(project)
