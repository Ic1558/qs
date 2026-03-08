from __future__ import annotations

import uuid
from typing import Any, Dict, List

def map_entities_to_segments(entities: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Maps stateless v1 entities to v2 project segments and candidates.
    Grouping by layer name.
    """
    segments = []
    candidates = []
    flags = []
    
    # Group entities by layer
    layers: Dict[str, List[Dict[str, Any]]] = {}
    for ent in entities:
        layer = ent.get("layer", "0")
        layers.setdefault(layer, []).append(ent)
        
    for layer_name, layer_entities in layers.items():
        # Heuristic for member name and type from layer
        # e.g. ST-B-G1 -> member B-G1, type beam
        member_id = layer_name
        member_type = "unknown"
        
        # Simple mapping heuristics
        upper_layer = layer_name.upper()
        if "BEAM" in upper_layer or "-B-" in upper_layer:
            member_type = "beam"
        elif "SLAB" in upper_layer or "-S-" in upper_layer:
            member_type = "slab"
        elif "COL" in upper_layer or "-C-" in upper_layer:
            member_type = "column"

        for ent in layer_entities:
            ent_type = ent.get("type", "").upper()
            
            if member_type == "beam":
                # LINE/POLYLINE with length
                length = ent.get("length_m", ent.get("length", 0.0))
                segments.append({
                    "member_id": member_id,
                    "member_type": "beam",
                    "segment_name": f"{layer_name}_{ent.get('handle', uuid.uuid4().hex[:4])}",
                    "length": length,
                    "width": ent.get("width_m", ent.get("width", 0.2)),
                    "depth": 0.0,
                    "basis_status": "DENSITY_FALLBACK",
                    "source_ref": f"layer:{layer_name}",
                })
                flags.append({
                    "flag_type": "density_fallback",
                    "target_ref": None,
                    "message": f"Beam segment in layer {layer_name} is missing width/depth.",
                })

            elif member_type == "slab":
                # CLOSED POLYLINE/HATCH with area
                area = ent.get("area_m2", ent.get("area", 0.0))
                thickness = ent.get("thickness", 0.15) or 0.15
                segments.append({
                    "member_id": member_id,
                    "member_type": "slab",
                    "segment_name": f"{layer_name}_{ent.get('handle', uuid.uuid4().hex[:4])}",
                    "area": area,
                    "length": ent.get("length", area or 1.0),
                    "width": ent.get("width", 1.0),
                    "depth": thickness,
                    "thickness": thickness,
                    "basis_status": "DENSITY_FALLBACK",
                    "source_ref": f"layer:{layer_name}",
                })
                flags.append({
                    "flag_type": "density_fallback",
                    "target_ref": None,
                    "message": f"Slab segment in layer {layer_name} is missing thickness.",
                })

            else:
                # Unknown category -> Candidate
                candidates.append({
                    "member_id": member_id,
                    "component_type": ent.get("type", "unknown"),
                    "qty": ent.get("length", ent.get("area", 1.0)),
                    "unit": "m" if "length" in ent else "m2" if "area" in ent else "set",
                    "line_type": "ADD",
                    "rate_context": "new",
                    "basis_status": "ADOPTED_DETAIL",
                    "source_ref": f"layer:{layer_name} handle:{ent.get('handle')}",
                    "review_note": f"Unclassified entity from layer {layer_name} type {ent.get('type')}",
                    "notes": "Created from drawing import",
                    "candidate_source": "drawing_import",
                    "candidate_type": "component_candidate",
                })

    return {
        "segments": segments,
        "candidates": candidates,
        "flags": flags,
    }
