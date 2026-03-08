from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from .domain_policy import DEFAULT_CALCULATION_POLICY
from .geometry_engine import GeometryFallback, compute_beam_slab_intersection, compute_member_net_volume
from .project_store import load_project, save_project
from .rate_library import resolve_rate


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


VOLUME_UNITS = {"m3", "m^3", "m³", "cu.m.", "cum"}


def _effective_segment(segment: Dict[str, Any]) -> Dict[str, Any]:
    effective = dict(segment)
    overrides = segment.get("overrides", {})
    for field in ("length", "width", "depth"):
        if field in overrides:
            effective[field] = overrides[field]
    return effective


def _segment_volume(segment: Dict[str, Any], member: Dict[str, Any]) -> float:
    effective = _effective_segment(segment)
    overrides = segment.get("overrides", {})
    length = float(effective.get("length", 0.0))
    width_val = float(effective.get("width", 0.0))
    depth_val = float(effective.get("depth", 0.0))
    width_override = "width" in overrides
    depth_override = "depth" in overrides
    width = width_val if width_val > 0.0 else (float(member.get("section_width", 0.0)) if width_override else 0.0)
    depth = depth_val if depth_val > 0.0 else (float(member.get("section_depth", 0.0)) if depth_override else 0.0)
    if length <= 0.0 or width <= 0.0 or depth <= 0.0:
        raise GeometryFallback("Segment still lacks positive geometry.")
    return length * width * depth


def _volume_qty_from_geometry(
    member: Dict[str, Any],
    component: Dict[str, Any],
    segments_by_member: Dict[str, list[dict[str, Any]]],
    segments_by_id: Dict[str, dict[str, Any]],
    members: Dict[str, dict[str, Any]],
) -> tuple[float, str | None]:
    member_type = str(member.get("member_type", "")).lower()
    if component.get("unit", "").lower() not in VOLUME_UNITS:
        return float(component.get("qty", 0.0)), None

    if component.get("source_segment_id"):
        segment = segments_by_id.get(component["source_segment_id"])
        if segment is None:
            return float(component.get("qty", 0.0)), "missing_source_segment"
        member_segments = [_effective_segment(segment)]
    else:
        member_segments = [_effective_segment(seg) for seg in segments_by_member.get(member.get("member_id", ""), [])]

    if member_type not in {"beam", "slab"} or not member_segments:
        return float(component.get("qty", 0.0)), None

    try:
        intersections: list[float] = []
        if member_type == "beam":
            slab_members = [item for item in members.values() if str(item.get("member_type", "")).lower() == "slab"]
            for beam_segment in member_segments:
                for slab_member in slab_members:
                    for slab_segment in segments_by_member.get(slab_member.get("member_id", ""), []):
                        vol = compute_beam_slab_intersection(beam_segment, slab_segment)
                        if vol > 0.0:
                            intersections.append(vol)
        resolution = "manual_allowance" if any(seg.get("overrides") for seg in segments_by_member.get(member.get("member_id", ""), [])) else None
        if component.get("source_segment_id") and segments_by_id.get(component["source_segment_id"], {}).get("overrides"):
            resolution = "manual_allowance"
        return compute_member_net_volume(member, member_segments, intersections), resolution
    except GeometryFallback:
        return float(component.get("qty", 0.0)), "density_fallback"


def rebuild_calc_graph(project_id: str) -> Dict[str, Any]:
    project = load_project(project_id)
    policy = {
        **DEFAULT_CALCULATION_POLICY,
        **project.get("project", {}).get("calculation_policy", {}),
    }
    members = {item["member_id"]: item for item in project["takeoff"]["members"]}
    segments_by_member: dict[str, list[dict[str, Any]]] = {}
    segments_by_id = {item["segment_id"]: item for item in project["takeoff"]["segments"]}
    for segment in project["takeoff"]["segments"]:
        segments_by_member.setdefault(segment.get("member_id", ""), []).append(segment)
    existing_rows = {row["calc_row_id"]: row for row in project.get("calc_graph", {}).get("rows", [])}
    existing_boq = {row["calc_row_ref"]: row for row in project.get("calc_graph", {}).get("boq_lines", [])}
    rows: list[dict[str, Any]] = []
    boq_lines: list[dict[str, Any]] = []
    dirty_all = bool(project.get("calc_graph", {}).get("dirty_all"))
    dirty_member_ids = {item["member_id"] for item in project["takeoff"]["members"] if item.get("dirty")}
    dirty_member_ids.update({seg["member_id"] for seg in project["takeoff"]["segments"] if seg.get("dirty")})

    for component in project["takeoff"]["components"]:
        source_seg = segments_by_id.get(component.get("source_segment_id", ""))
        is_dirty = dirty_all or component.get("dirty") or component.get("member_id") in dirty_member_ids or (source_seg and source_seg.get("dirty"))
        if not is_dirty and component["component_id"] in existing_rows:
            rows.append(existing_rows[component["component_id"]])
            if component["component_id"] in existing_boq:
                boq_lines.append(existing_boq[component["component_id"]])
            continue
        member = members.get(component["member_id"], {})
        qty, qty_resolution = _volume_qty_from_geometry(member, component, segments_by_member, segments_by_id, members)
        
        # Determine basis_status from geometry resolution if available, else use component/member value
        basis_status = (
            "DENSITY_FALLBACK"
            if qty_resolution == "density_fallback"
            else "MANUAL_ALLOWANCE"
            if qty_resolution == "manual_allowance"
            else component.get("basis_status", member.get("basis_status", "ADOPTED_DETAIL"))
        )

        is_dirty = dirty_all or component.get("dirty") or component.get("member_id") in dirty_member_ids or (source_seg and source_seg.get("dirty"))
        # If basis_status changed, we must treat it as dirty
        if not is_dirty and component["component_id"] in existing_rows:
            if existing_rows[component["component_id"]].get("basis_status") == basis_status:
                rows.append(existing_rows[component["component_id"]])
                if component["component_id"] in existing_boq:
                    boq_lines.append(existing_boq[component["component_id"]])
                continue

        loss_pct = float(component.get("loss_pct", 0.0))
        qty_with_loss = round(qty * (1 + loss_pct), 6)
        description = f"{member.get('member_code', '')} {component.get('spec') or component.get('component_type', '')}".strip()
        rates = resolve_rate(
            project,
            item_code=component.get("component_type", ""),
            description=description,
            rate_context=component.get("rate_context", "new"),
        )
        row = {
            "calc_row_id": component["component_id"],
            "member_id": component.get("member_id", ""),
            "source_segment_id": component.get("source_segment_id", ""),
            "member_code": member.get("member_code", ""),
            "desc": component.get("spec") or component.get("component_type", ""),
            "component_type": component.get("component_type", ""),
            "qty": qty,
            "qty_with_loss": qty_with_loss,
            "unit": component.get("unit", ""),
            "loss_pct": loss_pct,
            "line_type": component.get("line_type", "ADD"),
            "rate_context": component.get("rate_context", "new"),
            "abt_charged_override": component.get("abt_charged_override"),
            "material_rate": rates["material_rate"],
            "labor_rate": rates["labor_rate"],
            "machinery_rate": rates["machinery_rate"],
            "basis_status": basis_status,
            "formula_text": component.get("formula_text", "") if qty_resolution is None else f"{component.get('formula_text', '')} [{qty_resolution}]".strip(),
            "source_ref": component.get("source_ref", member.get("source_ref", "")),
            "review_flags": [],
        }
        rows.append(row)
        boq_lines.append(
            {
                "boq_line_id": f"boq_{component['component_id']}",
                "category": member.get("discipline", "structure"),
                "description": f"{member.get('member_code', '')} {row['desc']}".strip(),
                "qty": qty_with_loss,
                "unit": row["unit"],
                "line_type": row["line_type"],
                "rate_context": row["rate_context"],
                "abt_charged_override": row["abt_charged_override"],
                "mat_rate": row["material_rate"],
                "lab_rate": row["labor_rate"],
                "machinery_rate": row["machinery_rate"],
                "calc_row_ref": row["calc_row_id"],
                "source_ref": row["source_ref"],
                "basis_status": row["basis_status"],
            }
        )
        component["dirty"] = False

    for member in project["takeoff"]["members"]:
        member["dirty"] = False
    for segment in project["takeoff"]["segments"]:
        segment["dirty"] = False
    project["calc_graph"] = {
        "rows": rows,
        "boq_lines": boq_lines,
        "last_rebuild_at": _utc_now(),
        "dirty_all": False,
        "aggregation_policy": {
            "overlap_owner": policy["overlap_owner"],
            "formula_owner": policy["formula_owner"],
        },
    }
    save_project(project)
    return project["calc_graph"]
