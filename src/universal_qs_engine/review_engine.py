from __future__ import annotations

import hashlib
from typing import Any, Dict

from .domain_policy import EXPORT_RULES, MEMBER_TYPE_REQUIRED_FIELDS, REVIEW_SEVERITY
from .project_store import load_project, save_project


def _flag(severity: str, flag_type: str, target_ref: str, message: str, export_rule: str) -> dict[str, str]:
    flag = {
        "severity": severity,
        "flag_type": flag_type,
        "target_ref": target_ref,
        "message": message,
        "export_rule": export_rule,
        "resolution_status": "open",
    }
    flag["flag_id"] = compute_flag_id(flag)
    return flag


def compute_flag_id(flag: Dict[str, Any]) -> str:
    basis = "|".join(
        [
            str(flag.get("flag_type", "")),
            str(flag.get("target_ref", "")),
            str(flag.get("message", "")),
            str(flag.get("export_rule", "")),
        ]
    )
    return f"flag_{hashlib.sha1(basis.encode('utf-8')).hexdigest()[:12]}"


def _merge_resolution(flag: Dict[str, Any], resolutions: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    resolution = resolutions.get(flag["flag_id"])
    if not resolution:
        return flag
    merged = dict(flag)
    merged["resolution_kind"] = resolution.get("resolution_kind", "")
    merged["ack_comment"] = resolution.get("comment", "")
    merged["ack_timestamp"] = resolution.get("timestamp", "")
    
    if resolution.get("resolution_kind") == "ack_note":
        merged["resolution_status"] = "acknowledged"
        # block_owner flags remain blocking with ack_note
    elif resolution.get("resolution_kind") == "resolve_override":
        merged["resolution_status"] = "resolved"
        # Eligible classes are downgraded to warn_internal when overridden
        if flag["flag_type"] in {"density_fallback"}:
            merged["severity"] = REVIEW_SEVERITY["warn_internal"]
            
    return merged


def _missing_required_value(member: Dict[str, Any], field: str) -> bool:
    value = member.get(field)
    if isinstance(value, list):
        return len(value) == 0
    if isinstance(value, (int, float)):
        return float(value) <= 0.0
    return value in (None, "", {})


def rebuild_review_flags(project_id: str) -> list[dict[str, Any]]:
    project = load_project(project_id)
    resolutions = project.get("review_resolutions", {})
    flags: list[dict[str, Any]] = []
    segments_by_member: dict[str, list[dict[str, Any]]] = {}
    for segment in project["takeoff"]["segments"]:
        segments_by_member.setdefault(segment.get("member_id", ""), []).append(segment)

    for member in project["takeoff"]["members"]:
        ref = member.get("member_id", "")
        member_type = str(member.get("member_type", "")).lower()
        if not member.get("source_ref"):
            flags.append(_flag(REVIEW_SEVERITY["block_owner"], "missing_source", ref, "Member is missing source_ref.", EXPORT_RULES["block_owner"]))
        if not member.get("basis_status"):
            flags.append(_flag(REVIEW_SEVERITY["block_owner"], "missing_basis", ref, "Member is missing basis_status.", EXPORT_RULES["block_owner"]))
        if member.get("basis_status") == "EST_GRID":
            flags.append(_flag(REVIEW_SEVERITY["warn_internal"], "estimated_by_grid", ref, "Member still depends on EST_GRID basis.", EXPORT_RULES["warn_internal"]))
        for field in MEMBER_TYPE_REQUIRED_FIELDS.get(member_type, ()):
            if member_type == "pedestal" and field == "H_to_top_of_beam":
                continue
            if member_type == "beam" and field == "clear_span":
                continue
            if _missing_required_value(member, field):
                flags.append(
                    _flag(
                        REVIEW_SEVERITY["block_owner"],
                        "missing_member_field",
                        ref,
                        f"{member_type} member is missing required field: {field}.",
                        EXPORT_RULES["block_owner"],
                    )
                )
        if member_type == "beam" and float(member.get("clear_span", 0.0)) <= 0.0:
            flags.append(
                _flag(
                    REVIEW_SEVERITY["block_owner"],
                    "beam_span_unclosed",
                    ref,
                    "Beam clear_span is not closed. Block owner export until span is confirmed.",
                    EXPORT_RULES["block_owner"],
                )
            )
        if member_type == "slab":
            slab_segments = segments_by_member.get(ref, [])
            member_area_blocks = member.get("area_blocks", [])
            has_area_block = any(float(block.get("area", 0.0)) > 0.0 for block in member_area_blocks if isinstance(block, dict))
            has_segment_area = any(float(seg.get("area", 0.0)) > 0.0 for seg in slab_segments)
            if not has_area_block and not has_segment_area:
                flags.append(
                    _flag(
                        REVIEW_SEVERITY["block_owner"],
                        "slab_area_unclosed",
                        ref,
                        "Slab area block is not closed. Block owner export until slab area is confirmed.",
                        EXPORT_RULES["block_owner"],
                    )
                )
        if member_type == "pedestal":
            segments = segments_by_member.get(ref, [])
            if not any(float(seg.get("height", 0.0)) > 0 for seg in segments):
                flags.append(_flag(REVIEW_SEVERITY["block_owner"], "pedestal_h_unclosed", ref, "Pedestal H is not closed. Block calc output until height is confirmed.", EXPORT_RULES["block_owner"]))

    for component in project["takeoff"]["components"]:
        ref = component.get("component_id", "")
        if not component.get("source_ref"):
            flags.append(_flag(REVIEW_SEVERITY["block_owner"], "missing_source", ref, "Component is missing source_ref.", EXPORT_RULES["block_owner"]))
        if component.get("basis_status") == "DENSITY_FALLBACK":
            flags.append(_flag(REVIEW_SEVERITY["block_owner"], "density_fallback", ref, "Component uses density fallback.", EXPORT_RULES["block_owner"]))
        if component.get("basis_status") == "NEGOTIATED_COMMERCIAL" and component.get("abt_charged_override") in (None, ""):
            flags.append(_flag(REVIEW_SEVERITY["block_owner"], "missing_commercial_override", ref, "NEGOTIATED_COMMERCIAL requires abt_charged_override.", EXPORT_RULES["block_owner"]))

    for rate in project["rates"]:
        if not rate.get("rate_context"):
            flags.append(_flag(REVIEW_SEVERITY["warn_internal"], "missing_rate_context", rate.get("rate_id", ""), "Rate entry is missing rate_context.", EXPORT_RULES["warn_internal"]))

    for row in project.get("calc_graph", {}).get("rows", []):
        if float(row.get("material_rate", 0.0)) == 0.0 and float(row.get("labor_rate", 0.0)) == 0.0:
            flags.append(_flag(REVIEW_SEVERITY["warn_internal"], "missing_rate", row.get("calc_row_id", ""), "Calc row has no resolved rate.", EXPORT_RULES["warn_internal"]))

    for candidate in project.get("candidates", {}).get("components", []):
        if candidate.get("confirmation_status") == "pending":
            flags.append(
                _flag(
                    REVIEW_SEVERITY["info"],
                    "candidate_pending_confirmation",
                    candidate.get("candidate_id", ""),
                    "Candidate component is pending confirmation and excluded from final calc/export.",
                    EXPORT_RULES["warn_internal"],
                )
            )

    project["review_flags"] = [_merge_resolution(flag, resolutions) for flag in flags]
    save_project(project)
    return project["review_flags"]
