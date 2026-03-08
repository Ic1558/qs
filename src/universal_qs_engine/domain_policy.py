from __future__ import annotations


DEFAULT_CALCULATION_POLICY = {
    "overlap_owner": "manual_review",
    "formula_owner": "po_writer_only",
}

MEMBER_TYPE_REQUIRED_FIELDS = {
    "beam": ("member_code", "level", "grid_ref", "clear_span", "section_width", "section_depth"),
    "slab": ("member_code", "level", "slab_type", "thickness"),
    "pedestal": ("member_code", "level", "type_ref", "H_to_top_of_beam"),
    # Architecture
    "wall": ("member_code", "level", "wall_type", "height"),
    "opening": ("member_code", "parent_wall_id", "opening_type", "width", "height"),
    "finish": ("member_code", "parent_member_id", "finish_type", "net_area"),
    "area_block": ("member_code", "level", "zone_type", "gross_area"),
    # MEP
    "mep_count": ("member_code", "level", "item_type", "count"),
    "mep_run": ("member_code", "level", "service_type", "length"),
    "mep_riser": ("member_code", "system_type", "start_level", "end_level"),
}

LOSS_DEFAULTS = {
    "rebar": 0.07,
    "concrete": 0.03,
    "steel_anchor": 0.03,
    "chemical_anchor": 0.05,
}

BASIS_STATUSES = (
    "VERIFIED_DETAIL",
    "ADOPTED_DETAIL",
    "EST_GRID",
    "DENSITY_FALLBACK",
    "MANUAL_ALLOWANCE",
    "NEGOTIATED_COMMERCIAL",
)

REVIEW_SEVERITY = {
    "block_owner": "block_owner",
    "warn_internal": "warn_internal",
    "info": "info",
}

EXPORT_RULES = {
    "block_owner": "block_owner",
    "warn_internal": "warn_internal",
}

PEDESTAL_RULES = {
    "requires_closed_height": True,
}

AI_BOUNDARY = {
    "candidates_require_confirmation": True,
}
