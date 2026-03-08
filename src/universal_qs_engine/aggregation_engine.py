from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List
from .project_store import load_project, save_project
from .takeoff_workspace import add_component


def _compute_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def aggregate_project(project_id: str) -> Dict[str, Any]:
    project = load_project(project_id)
    members = project["takeoff"]["members"]
    segments = project["takeoff"]["segments"]
    
    # 1. Architecture Deductions (Wall -> Opening)
    # Group openings by parent_wall_id
    openings_by_wall: Dict[str, List[Dict[str, Any]]] = {}
    for m in members:
        if m.get("member_type") == "opening":
            parent_id = m.get("parent_wall_id")
            if parent_id:
                openings_by_wall.setdefault(parent_id, []).append(m)
                
    # Process walls
    for m in members:
        if m.get("member_type") == "wall":
            wall_id = m.get("member_id")
            gross_area = float(m.get("gross_area", 0.0))
            if gross_area <= 0.0:
                # Try to compute from segments if any
                wall_segments = [s for s in segments if s.get("member_id") == wall_id]
                gross_area = sum(float(s.get("area", 0.0)) for s in wall_segments)
                m["gross_area"] = gross_area
            
            # Deduct openings
            wall_openings = openings_by_wall.get(wall_id, [])
            total_deduction = sum(float(op.get("area", 0.0)) * float(op.get("count", 1.0)) for op in wall_openings)
            
            m["deductions"] = [
                {
                    "deducted_member_id": op.get("member_id"),
                    "rule_type": "opening_deduction",
                    "deducted_qty": float(op.get("area", 0.0)) * float(op.get("count", 1.0)),
                    "formula_text": f"Deduct {op.get('member_code')} area",
                }
                for op in wall_openings
            ]
            
            m["net_area"] = max(0.0, gross_area - total_deduction)
            
            # Update finish layers depending on this wall
            finishes = [f for f in members if f.get("member_type") == "finish" and f.get("parent_member_id") == wall_id]
            for f in finishes:
                f["net_area"] = m["net_area"]
                f["basis_status"] = m["basis_status"]
                f["source_ref"] = f"Derived from {m.get('member_code')}"

    # Save aggregated state after AR deductions
    save_project(project)

    # 2. MEP Aggregation (Run/Count)
    # Simple MEP aggregation: ensure each MEP member has at least one component if not already present
    for m in members:
        if m.get("discipline") == "mep":
            member_id = m.get("member_id")
            # Refresh project state to see newly added components from previous iterations
            current_project = load_project(project_id)
            existing_components = [c for c in current_project["takeoff"]["components"] if c.get("member_id") == member_id]
            if not existing_components:
                # Auto-create component based on MEP type
                m_type = m.get("member_type")
                qty = 0.0
                unit = "set"
                if m_type == "mep_count":
                    qty = float(m.get("count", 0.0))
                    unit = "set"
                elif m_type == "mep_run":
                    qty = float(m.get("length", 0.0))
                    unit = "m"
                
                if qty > 0:
                    add_component(project_id, {
                        "member_id": member_id,
                        "component_type": m.get("item_type") or m.get("service_type") or "MEP_ITEM",
                        "qty": qty,
                        "unit": unit,
                        "basis_status": m.get("basis_status", "ADOPTED_DETAIL"),
                        "source_ref": m.get("source_ref", ""),
                        "notes": "Auto-aggregated from MEP member",
                    })

    # Final reload to get the most up-to-date state including any auto-created components
    # before calc_graph rebuild
    from .calc_graph import rebuild_calc_graph
    return rebuild_calc_graph(project_id)
