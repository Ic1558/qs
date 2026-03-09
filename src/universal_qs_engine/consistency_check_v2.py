from __future__ import annotations

from typing import Any

from .errors import QSJobError
from .report_generate_v2 import _load_json_ref


def _normalize_boq(boq: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    candidates = (boq.get("items"), boq.get("lines"), boq.get("normalized_quantities"))
    items: list[dict[str, Any]] | None = None
    for value in candidates:
        if isinstance(value, list):
            items = value
            break
    if items is None:
        raise QSJobError("invalid_consistency_input:boq_items_not_list")

    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise QSJobError(f"invalid_consistency_input:boq_item_not_object:{index}")
        quantity_raw = item.get("quantity", item.get("qty", 0))
        try:
            quantity = float(quantity_raw)
        except (TypeError, ValueError) as exc:
            raise QSJobError(f"invalid_consistency_input:boq_quantity_invalid:{index}") from exc
        normalized.append(
            {
                "item_code": str(item.get("item_code") or item.get("code") or "").strip(),
                "quantity": round(quantity, 4),
            }
        )
    return normalized, len(normalized)


def _normalize_estimate(estimate: dict[str, Any]) -> tuple[list[dict[str, Any]], float]:
    line_items = estimate.get("line_items")
    if not isinstance(line_items, list):
        raise QSJobError("invalid_consistency_input:estimate_line_items_not_list")
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(line_items):
        if not isinstance(item, dict):
            raise QSJobError(f"invalid_consistency_input:estimate_line_item_not_object:{index}")
        quantity_raw = item.get("quantity", 0)
        try:
            quantity = float(quantity_raw)
        except (TypeError, ValueError) as exc:
            raise QSJobError(f"invalid_consistency_input:estimate_quantity_invalid:{index}") from exc
        normalized.append(
            {
                "item_code": str(item.get("item_code") or "").strip(),
                "quantity": round(quantity, 4),
            }
        )
    try:
        total_cost = float(estimate.get("total_cost"))
    except (TypeError, ValueError) as exc:
        raise QSJobError("invalid_consistency_input:estimate_total_cost_invalid") from exc
    return normalized, round(total_cost, 2)


def _normalize_po(po: dict[str, Any]) -> tuple[list[dict[str, Any]], float]:
    vendor = po.get("vendor")
    if not isinstance(vendor, dict):
        raise QSJobError("invalid_consistency_input:po_vendor_not_object")
    if not str(vendor.get("vendor_id") or "").strip():
        raise QSJobError("invalid_consistency_input:po_vendor_id_required")

    line_items = po.get("line_items")
    if not isinstance(line_items, list):
        raise QSJobError("invalid_consistency_input:po_line_items_not_list")
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(line_items):
        if not isinstance(item, dict):
            raise QSJobError(f"invalid_consistency_input:po_line_item_not_object:{index}")
        normalized.append(
            {
                "item_code": str(item.get("item_code") or "").strip(),
            }
        )
    try:
        total_cost = float(po.get("total_cost"))
    except (TypeError, ValueError) as exc:
        raise QSJobError("invalid_consistency_input:po_total_cost_invalid") from exc
    return normalized, round(total_cost, 2)


def _warning(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def check_consistency_v2(boq_ref: str, estimate_ref: str, po_ref: str) -> dict[str, Any]:
    boq = _load_json_ref(boq_ref, ref_name="boq_ref")
    estimate = _load_json_ref(estimate_ref, ref_name="estimate_ref")
    po = _load_json_ref(po_ref, ref_name="po_ref")

    boq_items, boq_count = _normalize_boq(boq)
    estimate_items, estimate_total_cost = _normalize_estimate(estimate)
    po_items, po_total_cost = _normalize_po(po)

    warnings: list[dict[str, str]] = []

    estimate_codes = {item["item_code"] for item in estimate_items if item["item_code"]}
    boq_codes = {item["item_code"] for item in boq_items if item["item_code"]}
    if boq_codes and estimate_codes:
        missing_mappings = sorted(code for code in boq_codes if code not in estimate_codes)
        if missing_mappings:
            warnings.append(
                _warning(
                    "boq_estimate_code_gap",
                    "BOQ item codes are missing from estimate mappings: " + ", ".join(missing_mappings),
                )
            )

    if boq_count != len(estimate_items):
        warnings.append(
            _warning(
                "boq_estimate_item_count_mismatch",
                f"BOQ item count ({boq_count}) does not match estimate item count ({len(estimate_items)})",
            )
        )

    if len(estimate_items) != len(po_items):
        warnings.append(
            _warning(
                "estimate_po_item_count_mismatch",
                f"Estimate item count ({len(estimate_items)}) does not match PO item count ({len(po_items)})",
            )
        )

    if abs(estimate_total_cost - po_total_cost) > 0.01:
        warnings.append(
            _warning(
                "estimate_po_total_cost_mismatch",
                f"Estimate total cost ({estimate_total_cost:.2f}) does not match PO total cost ({po_total_cost:.2f})",
            )
        )

    warnings = sorted(warnings, key=lambda item: (item["code"], item["message"]))

    boq_estimate_status = "warning" if any(
        item["code"] in {"boq_estimate_code_gap", "boq_estimate_item_count_mismatch"} for item in warnings
    ) else "ok"
    estimate_po_status = "warning" if any(
        item["code"] in {"estimate_po_item_count_mismatch", "estimate_po_total_cost_mismatch"} for item in warnings
    ) else "ok"
    overall_status = "warning" if warnings else "ok"

    return {
        "consistency_schema_version": "qs.consistency_check.v2",
        "status": overall_status,
        "checks": {
            "boq_estimate": boq_estimate_status,
            "estimate_po": estimate_po_status,
            "overall": overall_status,
        },
        "warnings": warnings,
        "summary": {
            "boq_items": boq_count,
            "estimate_items": len(estimate_items),
            "po_items": len(po_items),
            "estimate_total_cost": estimate_total_cost,
            "po_total_cost": po_total_cost,
        },
        "source_snapshot": {
            "boq_ref": str(boq_ref),
            "estimate_ref": str(estimate_ref),
            "po_ref": str(po_ref),
        },
    }
