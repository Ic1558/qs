from __future__ import annotations

import math
from typing import Any, Dict, List

import ezdxf

# Mapping rough prefixes to disciplines
DISCIPLINE_MAP = {
    'st': 'structure',
    's-': 'structure',
    'str-': 'structure',
    'beam': 'structure',
    'colm': 'structure',
    'a-': 'architecture',
    'b-wall': 'architecture',
    'wall': 'architecture',
    'm-': 'mep',
    'p-': 'mep',
    'e-': 'mep',
}


def guess_discipline_category(layer_name: str) -> tuple[str, str]:
    l_lower = layer_name.lower().strip()
    
    discipline = 'generic'
    for k, v in DISCIPLINE_MAP.items():
        if l_lower.startswith(k) or k in l_lower:
            discipline = v
            break
            
    # Guess Category
    category = 'generic'
    if 'beam' in l_lower:
        category = 'beam'
    elif 'col' in l_lower:
        category = 'column'
    elif 'footing' in l_lower:
        category = 'footing'
    elif 'wall' in l_lower:
        category = 'wall'
    elif 'stair' in l_lower:
        category = 'stair'
    elif 'slab' in l_lower or 'floor' in l_lower:
        category = 'slab'
    elif 'pipe' in l_lower or 'water' in l_lower or '\u0e17\u0e48\u0e2d\u0e19\u0e49\u0e33' in l_lower:  # Thai pipe text
        category = 'pipe'
    
    return discipline, category


def calculate_polyline_length(points, is_closed: bool = False) -> float:
    length = 0.0
    for i in range(1, len(points)):
        p1, p2 = points[i-1], points[i]
        # Ignore Z for 2D length
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        length += math.sqrt(dx*dx + dy*dy)
    if is_closed and len(points) > 2:
        p1, p2 = points[-1], points[0]
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        length += math.sqrt(dx*dx + dy*dy)
    return length


def calculate_polyline_area(points) -> float:
    # Shoelace formula
    if len(points) < 3:
        return 0.0
        
    area = 0.0
    j = len(points) - 1
    for i in range(len(points)):
        area += (points[j][0] + points[i][0]) * (points[j][1] - points[i][1])
        j = i
    return abs(area / 2.0)


def _scaled_length(value: float, scale_factor: float) -> float:
    return float(round(float(value) * scale_factor, 3))


def _scaled_area(value: float, scale_factor: float) -> float:
    return float(round(float(value) * (scale_factor ** 2), 3))


def _mark_review_required(entity: Dict[str, Any], reason: str) -> None:
    entity["review_required"] = True
    entity["review_reason"] = reason


def extract_dxf_entities(file_path: str, scale_factor: float = 0.001) -> Dict[str, Any]:
    try:
        doc = ezdxf.readfile(file_path)
    except Exception as e:
        raise ValueError(f"Failed to read DXF file: {e}")

    msp = doc.modelspace()
    results: List[Dict[str, Any]] = []
    review_queue: List[Dict[str, Any]] = []
    metrics = {
        "extractor": "ezdxf",
        "scale_factor_m_per_unit": scale_factor,
        "total_entities": 0,
        "kept_entities": 0,
        "skipped_annotations": 0,
        "generic_entities": 0,
        "geometry_measured_entities": 0,
        "review_required_entities": 0,
        "unresolved_area_entities": 0,
    }
    
    for idx, entity in enumerate(msp):
        metrics["total_entities"] += 1
        dxftype = entity.dxftype()
        layer = entity.dxf.layer if entity.dxf.hasattr('layer') else 'Unknown'
        
        # Skip pure annotations unless requested (DIMENSION, MTEXT, TEXT)
        if dxftype in ('TEXT', 'MTEXT', 'DIMENSION', 'LEADER', 'POINT'):
            metrics["skipped_annotations"] += 1
            continue
            
        discipline, category = guess_discipline_category(layer)
        
        ent_data = {
            "id": f"ent_{idx:05d}",
            "layer": layer,
            "type": dxftype.lower(),
            "discipline": discipline,
            "category": category,
        }
        
        if dxftype == 'LINE':
            start, end = entity.dxf.start, entity.dxf.end
            dx = end.x - start.x
            dy = end.y - start.y
            val = math.sqrt(dx*dx + dy*dy)
            ent_data['length_m'] = _scaled_length(val, scale_factor)
            metrics["geometry_measured_entities"] += 1
            
        elif dxftype == 'LWPOLYLINE':
            points = list(entity.vertices())
            # For 2D drawing, points are (x,y, bulge, start_width, end_width)
            # Just take x, y
            xy_points = [(p[0], p[1]) for p in points]
            
            val_len = calculate_polyline_length(xy_points, is_closed=entity.is_closed)
            ent_data['length_m'] = _scaled_length(val_len, scale_factor)
            metrics["geometry_measured_entities"] += 1
            if entity.is_closed:
                val_area = calculate_polyline_area(xy_points)
                ent_data['area_m2'] = _scaled_area(val_area, scale_factor)
                
        elif dxftype == 'HATCH':
            # ezdxf allows area calculations for simple boundaries if paths are polygonal
            # We'll try to extract boundary paths area if possible and otherwise
            # push the entity to manual review instead of inventing quantities.
            area = 0.0
            try:
                for path in entity.paths:
                    if str(path.type).endswith('PolylinePath'):
                        verts = [(v[0], v[1]) for v in path.vertices]
                        area += calculate_polyline_area(verts)
            except Exception:
                area = 0.0
            
            if area > 0:
                ent_data['area_m2'] = _scaled_area(area, scale_factor)
                metrics["geometry_measured_entities"] += 1
            else:
                _mark_review_required(ent_data, "unresolved_hatch_area")
                metrics["unresolved_area_entities"] += 1
                
        elif dxftype == 'CIRCLE':
            rad = entity.dxf.radius
            v_area = math.pi * (rad ** 2)
            v_len = 2 * math.pi * rad
            ent_data['area_m2'] = _scaled_area(v_area, scale_factor)
            ent_data['length_m'] = _scaled_length(v_len, scale_factor) # circumference
            metrics["geometry_measured_entities"] += 1
            
        elif dxftype == 'ARC':
            rad = entity.dxf.radius
            start = math.radians(entity.dxf.start_angle)
            end = math.radians(entity.dxf.end_angle)
            angle = end - start if end > start else (2*math.pi) - start + end
            val_len = rad * angle
            ent_data['length_m'] = _scaled_length(val_len, scale_factor)
            metrics["geometry_measured_entities"] += 1

        if category == 'generic':
            metrics["generic_entities"] += 1
        if ent_data.get("review_required"):
            metrics["review_required_entities"] += 1
            review_queue.append(
                {
                    "entity_id": ent_data["id"],
                    "layer": layer,
                    "type": dxftype.lower(),
                    "reason": ent_data["review_reason"],
                }
            )

        results.append(ent_data)
    
    metrics["kept_entities"] = len(results)
    return {
        "entities": results,
        "metrics": metrics,
        "review_queue": review_queue,
    }
