from __future__ import annotations

import uuid
from typing import Any, Dict

from .project_store import load_project, save_project


def add_source(project_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    project = load_project(project_id)
    source = {
        "source_id": payload.get("source_id") or f"src_{uuid.uuid4().hex[:8]}",
        "filename": payload.get("filename", ""),
        "path": payload.get("path", ""),
        "discipline": payload.get("discipline", "unknown"),
        "revision": payload.get("revision", ""),
        "issue_date": payload.get("issue_date", ""),
        "role": payload.get("role", "reference"),
        "sheet_code": payload.get("sheet_code", ""),
        "page_no": payload.get("page_no"),
        "notes": payload.get("notes", ""),
    }
    project["sources"].append(source)
    save_project(project)
    return source


def list_sources(project_id: str) -> list[dict[str, Any]]:
    return load_project(project_id)["sources"]

