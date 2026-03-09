from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .errors import QSJobError


def _load_json_ref(ref: str, *, ref_name: str) -> Any:
    normalized = str(ref or "").strip()
    if not normalized:
        raise QSJobError(f"invalid_cost_input:{ref_name}_required")
    path = Path(normalized)
    if path.suffix.lower() != ".json":
        raise QSJobError(f"invalid_cost_input:{ref_name}_unsupported_suffix:{path.suffix.lower() or 'missing'}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise QSJobError(f"invalid_cost_input:{ref_name}_missing") from exc
    except json.JSONDecodeError as exc:
        raise QSJobError(f"invalid_cost_input:{ref_name}_invalid_json") from exc


def _normalize_boq_line(raw: Any, *, index: int) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise QSJobError(f"invalid_cost_input:boq_line_not_object:{index}")
    item_code = str(raw.get("item_code") or raw.get("category") or "").strip()
    if not item_code:
        raise QSJobError(f"invalid_cost_input:boq_item_code_required:{index}")
    quantity = raw.get("quantity", raw.get("qty"))
    try:
        quantity_value = float(quantity)
    except (TypeError, ValueError) as exc:
        raise QSJobError(f"invalid_cost_input:boq_quantity_invalid:{index}") from exc
    unit = str(raw.get("unit") or "").strip()
    if not unit:
        raise QSJobError(f"invalid_cost_input:boq_unit_required:{index}")
    return {
        "item_code": item_code,
        "description": str(raw.get("description") or item_code).strip(),
        "quantity": quantity_value,
        "unit": unit,
    }


def _normalize_rate(raw: Any, *, index: int) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise QSJobError(f"invalid_cost_input:rate_not_object:{index}")
    item_code = str(raw.get("item_code") or raw.get("category") or "").strip()
    if not item_code:
        raise QSJobError(f"invalid_cost_input:rate_item_code_required:{index}")
    unit = str(raw.get("unit") or "").strip()
    if not unit:
        raise QSJobError(f"invalid_cost_input:rate_unit_required:{index}")
    try:
        unit_price = float(raw.get("unit_price"))
    except (TypeError, ValueError) as exc:
        raise QSJobError(f"invalid_cost_input:rate_unit_price_invalid:{index}") from exc
    return {
        "item_code": item_code,
        "unit": unit,
        "unit_price": unit_price,
    }


def estimate_cost_v2(*, boq_ref: str, price_snapshot_ref: str, currency: str = "THB") -> dict[str, Any]:
    boq_payload = _load_json_ref(boq_ref, ref_name="boq_ref")
    price_payload = _load_json_ref(price_snapshot_ref, ref_name="price_snapshot_ref")
    if not isinstance(boq_payload, dict):
        raise QSJobError("invalid_cost_input:boq_payload_not_object")
    if not isinstance(price_payload, dict):
        raise QSJobError("invalid_cost_input:price_snapshot_not_object")

    boq_lines_raw = boq_payload.get("items", boq_payload.get("lines"))
    rates_raw = price_payload.get("rates")
    if not isinstance(boq_lines_raw, list):
        raise QSJobError("invalid_cost_input:boq_lines_not_list")
    if not isinstance(rates_raw, list):
        raise QSJobError("invalid_cost_input:rates_not_list")

    boq_lines = [_normalize_boq_line(item, index=index) for index, item in enumerate(boq_lines_raw)]
    rates = {_normalize_rate(item, index=index)["item_code"]: _normalize_rate(item, index=index) for index, item in enumerate(rates_raw)}

    line_items: list[dict[str, Any]] = []
    for line in boq_lines:
        rate = rates.get(line["item_code"])
        if rate is None:
            raise QSJobError(f"invalid_cost_input:missing_rate:{line['item_code']}")
        if rate["unit"] != line["unit"]:
            raise QSJobError(f"invalid_cost_input:unit_mismatch:{line['item_code']}")
        total = round(line["quantity"] * rate["unit_price"], 2)
        line_items.append(
            {
                "item_code": line["item_code"],
                "description": line["description"],
                "quantity": line["quantity"],
                "unit": line["unit"],
                "unit_price": rate["unit_price"],
                "total_price": total,
            }
        )

    line_items.sort(key=lambda item: (str(item["item_code"]), str(item["description"])))
    total_cost = round(sum(item["total_price"] for item in line_items), 2)
    return {
        "currency": str(currency or "THB").strip() or "THB",
        "cost_schema_version": "qs.cost_estimate.v2",
        "line_items": line_items,
        "total_cost": total_cost,
        "source_snapshot": {
            "boq_ref": str(boq_ref),
            "price_snapshot_ref": str(price_snapshot_ref),
        },
    }
