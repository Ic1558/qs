from __future__ import annotations

from typing import Any, Dict, List
from .project_store import load_project, save_project
from .review_engine import rebuild_review_flags
from .calc_graph import rebuild_calc_graph


def evaluate_project_acceptance(project_id: str) -> Dict[str, Any]:
    project = load_project(project_id)
    # Ensure flags and calc graph are fresh
    review_flags = rebuild_review_flags(project_id)
    calc_graph = rebuild_calc_graph(project_id)
    
    # 1. No blocking flags
    blocking_flags = [f for f in review_flags if f.get("severity") == "block_owner" and f.get("resolution_status") != "resolved"]
    
    # 2. No density fallback
    density_flags = [f for f in review_flags if f.get("flag_type") == "density_fallback" and f.get("resolution_status") != "resolved"]
    
    # 3. All candidates processed
    pending_candidates = [c for c in project.get("candidates", {}).get("components", []) if c.get("confirmation_status") == "pending"]
    
    # 4. All rates resolved
    unrated_rows = [r for r in calc_graph.get("rows", []) if float(r.get("material_rate", 0.0)) == 0.0 and float(r.get("labor_rate", 0.0)) == 0.0]
    
    # 5. Source refs complete
    members_missing_source = [m for m in project.get("takeoff", {}).get("members", []) if not m.get("source_ref")]
    components_missing_source = [c for c in project.get("takeoff", {}).get("components", []) if not c.get("source_ref")]
    
    # 6. AR: Wall deductions complete
    unclosed_walls = [m for m in project.get("takeoff", {}).get("members", []) if m.get("member_type") == "wall" and float(m.get("net_area", 0.0)) <= 0.0]
    
    # 7. MEP: Runs/Counts closed
    unclosed_mep = [m for m in project.get("takeoff", {}).get("members", []) if m.get("discipline") == "mep" and (float(m.get("length", 0.0)) + float(m.get("count", 0.0))) <= 0.0]

    # 8. Unrated calc rows (Not block_owner but readiness)
    unrated_rows = [r for r in calc_graph.get("rows", []) if float(r.get("material_rate", 0.0)) == 0.0 and float(r.get("labor_rate", 0.0)) == 0.0]

    criteria = {
        "hard_gates_clear": len(blocking_flags) == 0,
        "geometry_closed": len(density_flags) == 0,
        "ai_candidates_resolved": len(pending_candidates) == 0,
        "rate_coverage_100pct": len(unrated_rows) == 0,
        "audit_link_integrity": (len(members_missing_source) + len(components_missing_source)) == 0,
        "ar_walls_closed": len(unclosed_walls) == 0,
        "mep_takeoff_closed": len(unclosed_mep) == 0,
    }
    
    override = project.get("acceptance_override")
    is_ok = all(criteria.values())
    if override and override.get("active"):
        is_ok = True
        
    return {
        "ok": is_ok,
        "criteria": criteria,
        "override": override,
        "summary": {
            "blocking_flags_count": len(blocking_flags),
            "density_flags_count": len(density_flags),
            "pending_candidates_count": len(pending_candidates),
            "unrated_rows_count": len(unrated_rows),
            "items_missing_source_count": len(members_missing_source) + len(components_missing_source),
        }
    }


def override_acceptance(project_id: str, justification: str, author: str) -> Dict[str, Any]:
    project = load_project(project_id)
    override = {
        "active": True,
        "justification": justification,
        "author": author,
        "timestamp": project.get("calc_graph", {}).get("last_rebuild_at", "") # Use last rebuild as proxy or just ISO now
    }
    project["acceptance_override"] = override
    save_project(project)
    return evaluate_project_acceptance(project_id)
