from __future__ import annotations

import uuid
from typing import Any, Dict

from .project_store import load_project, save_project


def add_rate(project_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    project = load_project(project_id)
    rate = {
        "rate_id": payload.get("rate_id") or f"rate_{uuid.uuid4().hex[:8]}",
        "item_code": payload.get("item_code", ""),
        "description": payload.get("description", ""),
        "unit": payload.get("unit", ""),
        "rate_context": payload.get("rate_context", "new"),
        "material_rate": float(payload.get("material_rate", 0.0)),
        "labor_rate": float(payload.get("labor_rate", 0.0)),
        "machinery_rate": float(payload.get("machinery_rate", 0.0)),
        "waste_mode": payload.get("waste_mode", "none"),
        "notes": payload.get("notes", ""),
    }
    project["rates"].append(rate)
    project.setdefault("calc_graph", {})["dirty_all"] = True
    for component in project.get("takeoff", {}).get("components", []):
        component["dirty"] = True
    save_project(project)
    return rate


def list_rates(project_id: str) -> list[dict[str, Any]]:
    return load_project(project_id)["rates"]


def resolve_rate(project: Dict[str, Any], *, item_code: str, description: str, rate_context: str) -> Dict[str, float]:
    for rate in project.get("rates", []):
        if rate.get("rate_context") != rate_context:
            continue
        if rate.get("item_code") == item_code or rate.get("item_code") in description:
            return {
                "material_rate": float(rate.get("material_rate", 0.0)),
                "labor_rate": float(rate.get("labor_rate", 0.0)),
                "machinery_rate": float(rate.get("machinery_rate", 0.0)),
            }
    return {"material_rate": 0.0, "labor_rate": 0.0, "machinery_rate": 0.0}
