from __future__ import annotations

import hashlib
import json
from typing import Any

from .errors import QSJobError


def _measurement_to_quantity_and_unit(measurements: dict[str, Any], *, index: int) -> tuple[float, str]:
    if "area_m2" in measurements:
        try:
            return round(float(measurements["area_m2"]), 4), "m2"
        except (TypeError, ValueError) as exc:
            raise QSJobError(f"invalid_continuity_input:boq_area_invalid:{index}") from exc
    if "length_m" in measurements:
        try:
            return round(float(measurements["length_m"]), 4), "m"
        except (TypeError, ValueError) as exc:
            raise QSJobError(f"invalid_continuity_input:boq_length_invalid:{index}") from exc
    raise QSJobError(f"invalid_continuity_input:boq_measurement_missing:{index}")


def make_cost_input_from_boq_v2(boq_payload: dict[str, Any], price_snapshot_ref: str) -> dict[str, Any]:
    if not isinstance(boq_payload, dict):
        raise QSJobError("invalid_continuity_input:boq_payload_not_object")
    if not str(price_snapshot_ref or "").strip():
        raise QSJobError("invalid_continuity_input:price_snapshot_ref_required")

    normalized_quantities = boq_payload.get("normalized_quantities")
    if not isinstance(normalized_quantities, list):
        raise QSJobError("invalid_continuity_input:normalized_quantities_not_list")

    items: list[dict[str, Any]] = []
    for index, item in enumerate(normalized_quantities):
        if not isinstance(item, dict):
            raise QSJobError(f"invalid_continuity_input:boq_item_not_object:{index}")
        item_code = str(item.get("item_code") or item.get("category") or "").strip()
        if not item_code:
            raise QSJobError(f"invalid_continuity_input:boq_item_code_required:{index}")
        measurements = item.get("measurements")
        if not isinstance(measurements, dict):
            raise QSJobError(f"invalid_continuity_input:boq_measurements_not_object:{index}")
        quantity, unit = _measurement_to_quantity_and_unit(measurements, index=index)
        items.append(
            {
                "item_code": item_code,
                "description": str(item.get("description") or item_code).strip(),
                "quantity": quantity,
                "unit": unit,
            }
        )

    items.sort(key=lambda row: (str(row["item_code"]), str(row["description"])))
    return {
        "boq_ref_payload": {
            "items": items,
        },
        "price_snapshot_ref": str(price_snapshot_ref),
    }


def make_po_input_from_estimate_v2(estimate_payload: dict[str, Any], vendor_ref: str, terms_template_id: str) -> dict[str, Any]:
    if not isinstance(estimate_payload, dict):
        raise QSJobError("invalid_continuity_input:estimate_payload_not_object")
    if not str(vendor_ref or "").strip():
        raise QSJobError("invalid_continuity_input:vendor_ref_required")
    if not str(terms_template_id or "").strip():
        raise QSJobError("invalid_continuity_input:terms_template_id_required")

    line_items = estimate_payload.get("line_items")
    if not isinstance(line_items, list):
        raise QSJobError("invalid_continuity_input:estimate_line_items_not_list")
    try:
        total_cost = round(float(estimate_payload.get("total_cost")), 2)
    except (TypeError, ValueError) as exc:
        raise QSJobError("invalid_continuity_input:estimate_total_cost_invalid") from exc

    normalized_lines: list[dict[str, Any]] = []
    for index, item in enumerate(line_items):
        if not isinstance(item, dict):
            raise QSJobError(f"invalid_continuity_input:estimate_line_item_not_object:{index}")
        item_code = str(item.get("item_code") or "").strip()
        unit = str(item.get("unit") or "").strip()
        if not item_code:
            raise QSJobError(f"invalid_continuity_input:estimate_item_code_required:{index}")
        if not unit:
            raise QSJobError(f"invalid_continuity_input:estimate_unit_required:{index}")
        try:
            quantity = float(item.get("quantity"))
            unit_price = float(item.get("unit_price"))
        except (TypeError, ValueError) as exc:
            raise QSJobError(f"invalid_continuity_input:estimate_values_invalid:{index}") from exc
        normalized_lines.append(
            {
                "item_code": item_code,
                "description": str(item.get("description") or item_code).strip(),
                "quantity": quantity,
                "unit": unit,
                "unit_price": unit_price,
            }
        )

    normalized_lines.sort(key=lambda row: (str(row["item_code"]), str(row["description"])))
    estimate_id = str(estimate_payload.get("estimate_id") or "").strip()
    if not estimate_id:
        source_snapshot = estimate_payload.get("source_snapshot")
        if isinstance(source_snapshot, dict):
            estimate_seed = str(source_snapshot.get("boq_ref") or "").strip()
        else:
            estimate_seed = ""
        seed_material = json.dumps(
            {
                "boq_ref": estimate_seed,
                "total_cost": total_cost,
                "line_items": normalized_lines,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        estimate_id = "estimate_auto_" + hashlib.sha256(seed_material.encode("utf-8")).hexdigest()[:12]

    return {
        "estimate_ref_payload": {
            "estimate_id": estimate_id,
            "line_items": normalized_lines,
            "total_cost": total_cost,
            "currency": str(estimate_payload.get("currency") or "").strip() or "THB",
        },
        "vendor_ref": str(vendor_ref),
        "terms_template_id": str(terms_template_id),
    }
