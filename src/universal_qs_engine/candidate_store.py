from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from .project_store import load_project, save_project


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _candidate_component_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "member_id": payload.get("member_id", ""),
        "component_type": payload.get("component_type", ""),
        "spec": payload.get("spec", ""),
        "qty": float(payload.get("qty", 0.0)),
        "unit": payload.get("unit", ""),
        "loss_pct": float(payload.get("loss_pct", 0.0)),
        "line_type": payload.get("line_type", "ADD"),
        "rate_context": payload.get("rate_context", "new"),
        "abt_charged_override": payload.get("abt_charged_override"),
        "basis_status": payload.get("basis_status", "ADOPTED_DETAIL"),
        "formula_text": payload.get("formula_text", ""),
        "source_ref": payload.get("source_ref", ""),
        "notes": payload.get("notes", ""),
    }


def add_component_candidate(project_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    project = load_project(project_id)
    candidate = {
        "candidate_id": payload.get("candidate_id") or f"cand_{uuid.uuid4().hex[:8]}",
        "candidate_type": "component_candidate",
        "candidate_source": payload.get("candidate_source", "ai_assist"),
        "ai_origin": payload.get("ai_origin", {}),
        "confirmation_status": "pending",
        "proposed_component": _candidate_component_payload(payload),
        "review_note": payload.get("review_note", ""),
        "resolution_reason": "",
        "created_at": _utc_now(),
        "confirmed_at": None,
        "confirmed_component_id": None,
    }
    project.setdefault("candidates", {}).setdefault("components", []).append(candidate)
    save_project(project)
    return candidate


def list_component_candidates(project_id: str) -> list[dict[str, Any]]:
    project = load_project(project_id)
    return project.get("candidates", {}).get("components", [])


def confirm_component_candidate(project_id: str, candidate_id: str, reason: str = "") -> Dict[str, Any]:
    project = load_project(project_id)
    candidates = project.setdefault("candidates", {}).setdefault("components", [])
    candidate = next((item for item in candidates if item.get("candidate_id") == candidate_id), None)
    if not candidate:
        raise KeyError(candidate_id)
    if candidate.get("confirmation_status") == "confirmed":
        return candidate

    proposed = dict(candidate.get("proposed_component", {}))
    proposed["component_id"] = proposed.get("component_id") or f"cmp_{uuid.uuid4().hex[:8]}"
    proposed["dirty"] = True
    project.setdefault("takeoff", {}).setdefault("components", []).append(proposed)
    candidate["confirmation_status"] = "confirmed"
    candidate["confirmed_at"] = _utc_now()
    candidate["confirmed_component_id"] = proposed["component_id"]
    candidate["resolution_reason"] = reason
    save_project(project)
    return candidate


def reject_component_candidate(project_id: str, candidate_id: str, reason: str = "") -> Dict[str, Any]:
    project = load_project(project_id)
    candidates = project.setdefault("candidates", {}).setdefault("components", [])
    candidate = next((item for item in candidates if item.get("candidate_id") == candidate_id), None)
    if not candidate:
        raise KeyError(candidate_id)
    candidate["confirmation_status"] = "rejected"
    candidate["resolution_reason"] = reason
    candidate["confirmed_at"] = _utc_now()
    save_project(project)
    return candidate
