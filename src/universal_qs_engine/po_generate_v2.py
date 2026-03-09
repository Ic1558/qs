from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .errors import QSJobError


def _load_json_ref(ref: str, *, ref_name: str) -> dict[str, Any]:
    normalized = str(ref or "").strip()
    if not normalized:
        raise QSJobError(f"invalid_po_input:{ref_name}_required")
    path = Path(normalized)
    if path.suffix.lower() != ".json":
        raise QSJobError(f"invalid_po_input:{ref_name}_unsupported_suffix:{path.suffix.lower() or 'missing'}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise QSJobError(f"invalid_po_input:{ref_name}_missing") from exc
    except json.JSONDecodeError as exc:
        raise QSJobError(f"invalid_po_input:{ref_name}_invalid_json") from exc
    if not isinstance(payload, dict):
        raise QSJobError(f"invalid_po_input:{ref_name}_not_object")
    return payload


def _normalize_vendor(payload: dict[str, Any]) -> dict[str, str]:
    vendor_id = str(payload.get("vendor_id") or "").strip()
    vendor_name = str(payload.get("vendor_name") or "").strip()
    payment_terms = str(payload.get("payment_terms") or "").strip()
    if not vendor_id:
        raise QSJobError("invalid_po_input:vendor_id_required")
    if not vendor_name:
        raise QSJobError("invalid_po_input:vendor_name_required")
    if not payment_terms:
        raise QSJobError("invalid_po_input:payment_terms_required")
    return {
        "vendor_id": vendor_id,
        "vendor_name": vendor_name,
        "payment_terms": payment_terms,
    }


def _normalize_estimate_lines(payload: dict[str, Any]) -> tuple[str, list[dict[str, Any]], float]:
    estimate_id = str(payload.get("estimate_id") or "").strip()
    if not estimate_id:
        raise QSJobError("invalid_po_input:estimate_id_required")
    line_items = payload.get("line_items")
    total_cost = payload.get("total_cost")
    if not isinstance(line_items, list):
        raise QSJobError("invalid_po_input:estimate_line_items_not_list")
    try:
        total_cost_value = float(total_cost)
    except (TypeError, ValueError) as exc:
        raise QSJobError("invalid_po_input:estimate_total_cost_invalid") from exc

    normalized_lines: list[dict[str, Any]] = []
    for index, raw in enumerate(line_items):
        if not isinstance(raw, dict):
            raise QSJobError(f"invalid_po_input:estimate_line_not_object:{index}")
        item_code = str(raw.get("item_code") or "").strip()
        description = str(raw.get("description") or item_code).strip()
        unit = str(raw.get("unit") or "").strip()
        if not item_code:
            raise QSJobError(f"invalid_po_input:estimate_item_code_required:{index}")
        if not unit:
            raise QSJobError(f"invalid_po_input:estimate_unit_required:{index}")
        try:
            quantity = float(raw.get("quantity"))
            unit_price = float(raw.get("unit_price"))
        except (TypeError, ValueError) as exc:
            raise QSJobError(f"invalid_po_input:estimate_values_invalid:{index}") from exc
        line_total = round(quantity * unit_price, 2)
        normalized_lines.append(
            {
                "item_code": item_code,
                "description": description,
                "quantity": quantity,
                "unit": unit,
                "unit_price": unit_price,
                "line_total": line_total,
            }
        )
    normalized_lines.sort(key=lambda item: (item["item_code"], item["description"]))
    return estimate_id, normalized_lines, round(total_cost_value, 2)


def generate_po_v2(*, estimate_ref: str, vendor_ref: str, terms_template_id: str) -> dict[str, Any]:
    template_id = str(terms_template_id or "").strip()
    if not template_id:
        raise QSJobError("invalid_po_input:terms_template_id_required")

    estimate_payload = _load_json_ref(estimate_ref, ref_name="estimate_ref")
    vendor_payload = _load_json_ref(vendor_ref, ref_name="vendor_ref")
    vendor = _normalize_vendor(vendor_payload)
    estimate_id, line_items, total_cost = _normalize_estimate_lines(estimate_payload)

    sections = [
        {"section": "header", "label": "Purchase Order"},
        {"section": "vendor", "label": vendor["vendor_name"]},
        {"section": "commercials", "label": vendor["payment_terms"]},
        {"section": "totals", "label": f"{total_cost:.2f}"},
    ]
    return {
        "po_schema_version": "qs.po_generate.v2",
        "terms_template_id": template_id,
        "estimate_id": estimate_id,
        "vendor": vendor,
        "line_items": line_items,
        "total_cost": total_cost,
        "sections": sections,
        "source_snapshot": {
            "estimate_ref": str(estimate_ref),
            "vendor_ref": str(vendor_ref),
        },
    }
