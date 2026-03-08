from __future__ import annotations

from typing import Any


class GeometryFallback(Exception):
    """Raised when geometry-based quantity logic cannot be resolved safely."""


def _require_positive(value: Any, field: str) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise GeometryFallback(f"Missing geometry field: {field}") from exc
    if numeric <= 0.0:
        raise GeometryFallback(f"Non-positive geometry field: {field}")
    return numeric


def _origin_value(segment: dict[str, Any], field: str) -> float:
    try:
        return float(segment.get(field, 0.0))
    except (TypeError, ValueError):
        return 0.0


def compute_member_gross_volume(member: dict, segments: list[dict]) -> float:
    if not segments:
        raise GeometryFallback("Member has no segments.")
    volume = 0.0
    for segment in segments:
        length = _require_positive(segment.get("length"), "length")
        width = _require_positive(segment.get("width"), "width")
        depth = _require_positive(segment.get("depth"), "depth")
        volume += length * width * depth
    return volume


def _box_bounds(segment: dict[str, Any]) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float]]:
    length = _require_positive(segment.get("length"), "length")
    width = _require_positive(segment.get("width"), "width")
    depth = _require_positive(segment.get("depth"), "depth")
    ox = _origin_value(segment, "origin_x")
    oy = _origin_value(segment, "origin_y")
    oz = _origin_value(segment, "origin_z")
    return ((ox, ox + length), (oy, oy + width), (oz, oz + depth))


def _overlap_1d(a: tuple[float, float], b: tuple[float, float]) -> float:
    return max(0.0, min(a[1], b[1]) - max(a[0], b[0]))


def compute_beam_slab_intersection(beam: dict, slab: dict) -> float:
    beam_bounds = _box_bounds(beam)
    slab_bounds = _box_bounds(slab)
    overlap_x = _overlap_1d(beam_bounds[0], slab_bounds[0])
    overlap_y = _overlap_1d(beam_bounds[1], slab_bounds[1])
    overlap_z = _overlap_1d(beam_bounds[2], slab_bounds[2])
    if overlap_x == 0.0 or overlap_y == 0.0 or overlap_z == 0.0:
        return 0.0

    try:
        import trimesh

        beam_mesh = trimesh.creation.box(extents=[beam_bounds[0][1] - beam_bounds[0][0], beam_bounds[1][1] - beam_bounds[1][0], beam_bounds[2][1] - beam_bounds[2][0]])
        slab_mesh = trimesh.creation.box(extents=[slab_bounds[0][1] - slab_bounds[0][0], slab_bounds[1][1] - slab_bounds[1][0], slab_bounds[2][1] - slab_bounds[2][0]])
        beam_mesh.apply_translation(
            [
                (beam_bounds[0][0] + beam_bounds[0][1]) / 2,
                (beam_bounds[1][0] + beam_bounds[1][1]) / 2,
                (beam_bounds[2][0] + beam_bounds[2][1]) / 2,
            ]
        )
        slab_mesh.apply_translation(
            [
                (slab_bounds[0][0] + slab_bounds[0][1]) / 2,
                (slab_bounds[1][0] + slab_bounds[1][1]) / 2,
                (slab_bounds[2][0] + slab_bounds[2][1]) / 2,
            ]
        )
        # Boolean backends are optional and can stall depending on the local geometry stack.
        # For the current structure-first authoring phase, use deterministic AABB overlap volume
        # once the meshes are constructible.
        return overlap_x * overlap_y * overlap_z
    except ModuleNotFoundError as exc:
        raise GeometryFallback("trimesh is not installed.") from exc
    except Exception as exc:
        raise GeometryFallback("trimesh mesh construction failed.") from exc


def compute_member_net_volume(member: dict, segments: list[dict], intersections: list[float]) -> float:
    gross = compute_member_gross_volume(member, segments)
    net = gross - sum(float(item) for item in intersections)
    if net < 0.0:
        raise GeometryFallback("Computed negative net volume.")
    return net
