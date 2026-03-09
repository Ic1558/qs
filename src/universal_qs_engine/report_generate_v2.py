from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .errors import QSJobError


def _load_json_ref(ref: str, *, ref_name: str) -> dict[str, Any]:
    normalized = str(ref or "").strip()
    if not normalized:
        raise QSJobError(f"invalid_report_input:{ref_name}_required")
    path = Path(normalized)
    if path.suffix.lower() != ".json":
        raise QSJobError(f"invalid_report_input:{ref_name}_unsupported_suffix:{path.suffix.lower() or 'missing'}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise QSJobError(f"invalid_report_input:{ref_name}_missing") from exc
    except json.JSONDecodeError as exc:
        raise QSJobError(f"invalid_report_input:{ref_name}_invalid_json") from exc
    if not isinstance(payload, dict):
        raise QSJobError(f"invalid_report_input:{ref_name}_not_object")
    return payload


def _count_boq_items(boq: dict[str, Any]) -> int:
    candidates = (boq.get("items"), boq.get("lines"), boq.get("normalized_quantities"))
    for value in candidates:
        if isinstance(value, list):
            return len(value)
    return 0


def _normalize_estimate(estimate: dict[str, Any]) -> tuple[str, float, str | None]:
    estimate_id = str(estimate.get("estimate_id") or "").strip()
    if not estimate_id:
        raise QSJobError("invalid_report_input:estimate_id_required")
    line_items = estimate.get("line_items")
    if not isinstance(line_items, list):
        raise QSJobError("invalid_report_input:estimate_line_items_not_list")
    try:
        total_cost = float(estimate.get("total_cost"))
    except (TypeError, ValueError) as exc:
        raise QSJobError("invalid_report_input:estimate_total_cost_invalid") from exc
    currency = estimate.get("currency")
    currency_value = str(currency).strip() if currency is not None else None
    return estimate_id, round(total_cost, 2), currency_value or None


def _normalize_po(po: dict[str, Any]) -> tuple[float, str | None]:
    vendor = po.get("vendor")
    if not isinstance(vendor, dict):
        raise QSJobError("invalid_report_input:po_vendor_not_object")
    if not str(vendor.get("vendor_id") or "").strip():
        raise QSJobError("invalid_report_input:po_vendor_id_required")
    line_items = po.get("line_items")
    if not isinstance(line_items, list):
        raise QSJobError("invalid_report_input:po_line_items_not_list")
    try:
        total_cost = float(po.get("total_cost"))
    except (TypeError, ValueError) as exc:
        raise QSJobError("invalid_report_input:po_total_cost_invalid") from exc
    currency = po.get("currency")
    currency_value = str(currency).strip() if currency is not None else None
    return round(total_cost, 2), currency_value or None


def compose_report_v2(
    *,
    boq_ref: str,
    estimate_ref: str,
    po_ref: str,
    report_profile_id: str,
) -> dict[str, Any]:
    profile = str(report_profile_id or "").strip()
    if not profile:
        raise QSJobError("invalid_report_input:report_profile_id_required")

    boq = _load_json_ref(boq_ref, ref_name="boq_ref")
    estimate = _load_json_ref(estimate_ref, ref_name="estimate_ref")
    po = _load_json_ref(po_ref, ref_name="po_ref")

    boq_items = _count_boq_items(boq)
    estimate_id, estimate_total_cost, estimate_currency = _normalize_estimate(estimate)
    po_total_cost, po_currency = _normalize_po(po)

    currency = estimate_currency or po_currency
    warnings: list[str] = []
    if estimate_currency and po_currency and estimate_currency != po_currency:
        warnings.append("currency_mismatch")
    if abs(estimate_total_cost - po_total_cost) > 0.01:
        warnings.append("total_cost_mismatch")

    return {
        "report_schema_version": "qs.report_generate.v2",
        "report_profile_id": profile,
        "summary": {
            "boq_items": int(boq_items),
            "estimate_id": estimate_id,
            "estimate_total_cost": estimate_total_cost,
            "po_total_cost": po_total_cost,
            "currency": currency,
        },
        "sections": [
            "executive_summary",
            "boq_summary",
            "cost_summary",
            "po_summary",
        ],
        "warnings": warnings,
        "source_snapshot": {
            "boq_ref": str(boq_ref),
            "estimate_ref": str(estimate_ref),
            "po_ref": str(po_ref),
        },
    }

