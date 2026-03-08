from __future__ import annotations

import uuid
from typing import Any, Dict

from .domain_policy import MEMBER_TYPE_REQUIRED_FIELDS
from .project_store import load_project, save_project


NUMERIC_MEMBER_FIELDS = {
    "clear_span",
    "section_width",
    "section_depth",
    "thickness",
    "H_to_top_of_beam",
    "footing_offset",
    "main_bar_count",
    "main_bar_dia",
    "tie_dia",
    "tie_spacing",
    "drilled_bar_count",
    "drill_depth",
    "hilti_count",
    # AR
    "height",
    "width",
    "gross_area",
    "net_area",
    "count",
    "length",
    # MEP
}

LIST_MEMBER_FIELDS = {
    "extension_segments",
    "stirrup_zones",
    "steel_embeds",
    "anchor_zones",
    "area_blocks",
    "opening_deductions",
    # AR
    "deductions",
}


def _member_field_default(field: str) -> Any:
    if field in NUMERIC_MEMBER_FIELDS:
        return 0.0
    if field in LIST_MEMBER_FIELDS:
        return []
    return ""


def _apply_extra_member_fields(member: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    for key, value in payload.items():
        if key in member:
            continue
        if key in NUMERIC_MEMBER_FIELDS:
            member[key] = float(value or 0.0)
        elif key in LIST_MEMBER_FIELDS:
            member[key] = list(value or [])
        else:
            member[key] = value
    return member


def add_member(project_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    project = load_project(project_id)
    member = {
        "member_id": payload.get("member_id") or f"mem_{uuid.uuid4().hex[:8]}",
        "discipline": payload.get("discipline", "structure"),
        "member_type": payload.get("member_type", ""),
        "member_code": payload.get("member_code", ""),
        "level": payload.get("level", ""),
        "basis_status": payload.get("basis_status", "ADOPTED_DETAIL"),
        "source_ref": payload.get("source_ref", ""),
        "execution_status": payload.get("execution_status", "NOT_STARTED"),
        "notes": payload.get("notes", ""),
        "dirty": True,
    }
    member = _apply_extra_member_fields(member, payload)
    project["takeoff"]["members"].append(member)
    save_project(project)
    return member


def _normalize_typed_payload(member_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(payload)
    
    # Set discipline based on member_type
    if member_type in {"beam", "slab", "pedestal"}:
        normalized["discipline"] = payload.get("discipline", "structure")
    elif member_type in {"wall", "opening", "finish", "area_block"}:
        normalized["discipline"] = payload.get("discipline", "architecture")
    elif member_type in {"mep_count", "mep_run", "mep_riser"}:
        normalized["discipline"] = payload.get("discipline", "mep")
    else:
        normalized["discipline"] = payload.get("discipline", "structure")

    normalized["member_type"] = member_type
    for field in MEMBER_TYPE_REQUIRED_FIELDS.get(member_type, ()):
        normalized.setdefault(field, _member_field_default(field))
    
    # Structure defaults
    if member_type == "beam":
        normalized.setdefault("grid_ref", "")
        normalized.setdefault("extension_segments", [])
        normalized.setdefault("stirrup_zones", [])
        normalized.setdefault("steel_embeds", [])
        normalized.setdefault("anchor_zones", [])
    elif member_type == "slab":
        normalized.setdefault("slab_type", "")
        normalized.setdefault("thickness", 0.0)
        normalized.setdefault("area_blocks", [])
        normalized.setdefault("opening_deductions", [])
    elif member_type == "pedestal":
        normalized.setdefault("type_ref", "")
        normalized.setdefault("H_to_top_of_beam", 0.0)
        normalized.setdefault("footing_offset", 0.05)
        normalized.setdefault("main_bar_count", 0.0)
        normalized.setdefault("main_bar_dia", 0.0)
        normalized.setdefault("tie_dia", 0.0)
        normalized.setdefault("tie_spacing", 0.0)
        normalized.setdefault("drilled_bar_count", 0.0)
        normalized.setdefault("drill_depth", 0.0)
        normalized.setdefault("hilti_count", 0.0)
    
    # AR defaults
    elif member_type == "wall":
        normalized.setdefault("wall_type", "")
        normalized.setdefault("height", 0.0)
        normalized.setdefault("location_tag", "")
    elif member_type == "opening":
        normalized.setdefault("parent_wall_id", "")
        normalized.setdefault("opening_type", "")
    elif member_type == "finish":
        normalized.setdefault("parent_member_id", "")
        normalized.setdefault("finish_type", "")
        normalized.setdefault("coverage_basis", "")
    elif member_type == "area_block":
        normalized.setdefault("zone_type", "")
        
    # MEP defaults
    elif member_type == "mep_count":
        normalized.setdefault("item_type", "")
    elif member_type == "mep_run":
        normalized.setdefault("service_type", "")
    elif member_type == "mep_riser":
        normalized.setdefault("system_type", "")
        normalized.setdefault("start_level", "")
        normalized.setdefault("end_level", "")

    return normalized


def add_member_beam(project_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return add_member(project_id, _normalize_typed_payload("beam", payload))


def add_member_slab(project_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return add_member(project_id, _normalize_typed_payload("slab", payload))


def add_member_pedestal(project_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return add_member(project_id, _normalize_typed_payload("pedestal", payload))


def add_member_wall(project_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return add_member(project_id, _normalize_typed_payload("wall", payload))


def add_member_opening(project_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return add_member(project_id, _normalize_typed_payload("opening", payload))


def add_member_finish(project_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return add_member(project_id, _normalize_typed_payload("finish", payload))


def add_member_area_block(project_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return add_member(project_id, _normalize_typed_payload("area_block", payload))


def add_member_mep_count(project_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return add_member(project_id, _normalize_typed_payload("mep_count", payload))


def add_member_mep_run(project_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return add_member(project_id, _normalize_typed_payload("mep_run", payload))


def add_member_mep_riser(project_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return add_member(project_id, _normalize_typed_payload("mep_riser", payload))


def add_segment(project_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    project = load_project(project_id)
    segment = {
        "segment_id": payload.get("segment_id") or f"seg_{uuid.uuid4().hex[:8]}",
        "member_id": payload.get("member_id", ""),
        "segment_name": payload.get("segment_name", ""),
        "length": float(payload.get("length", 0.0)),
        "width": float(payload.get("width", 0.0)),
        "depth": float(payload.get("depth", 0.0)),
        "height": float(payload.get("height", 0.0)),
        "area": float(payload.get("area", 0.0)),
        "volume": float(payload.get("volume", 0.0)),
        "basis_status": payload.get("basis_status", "ADOPTED_DETAIL"),
        "formula_text": payload.get("formula_text", ""),
        "source_ref": payload.get("source_ref", ""),
        "origin_x": float(payload.get("origin_x", 0.0)),
        "origin_y": float(payload.get("origin_y", 0.0)),
        "origin_z": float(payload.get("origin_z", 0.0)),
        "notes": payload.get("notes", ""),
        "dirty": True,
    }
    project["takeoff"]["segments"].append(segment)
    save_project(project)
    return segment


def add_component(project_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    project = load_project(project_id)
    component = {
        "component_id": payload.get("component_id") or f"cmp_{uuid.uuid4().hex[:8]}",
        "member_id": payload.get("member_id", ""),
        "source_segment_id": payload.get("source_segment_id", ""),
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
        "dirty": True,
    }
    project["takeoff"]["components"].append(component)
    save_project(project)
    return component


def get_takeoff(project_id: str) -> Dict[str, Any]:
    return load_project(project_id)["takeoff"]
