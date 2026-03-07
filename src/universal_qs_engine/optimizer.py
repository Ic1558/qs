from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from .contracts import TakeoffRequest


def _source_cost_tier(source) -> str:
    if source.format in {"dwg", "dxf"}:
        return "low"
    if source.format == "pdf" and source.vector_pdf:
        return "medium"
    return "high"


def build_optimization_plan(request: TakeoffRequest, review_required: bool) -> Dict[str, Any]:
    config = request.config
    tiers = Counter(_source_cost_tier(source) for source in request.sources)
    actions: List[Dict[str, Any]] = []

    if any(source.format in {"dwg", "dxf"} for source in request.sources):
        actions.append(
            {
                "priority": "highest",
                "action": "prefer_vector_sources",
                "reason": "DWG/DXF extraction is cheaper and more deterministic than OCR.",
            }
        )
    if any(source.format == "pdf" and source.vector_pdf for source in request.sources):
        actions.append(
            {
                "priority": "high",
                "action": "skip_ocr_for_vector_pdf",
                "reason": "Use native PDF geometry/text before OCR.",
            }
        )
    if any(source.format == "pdf" and not source.vector_pdf for source in request.sources):
        actions.append(
            {
                "priority": "high",
                "action": "ocr_only_on_target_pages",
                "reason": "Run OCR and symbol detection only on pages needed for unmapped scopes.",
            }
        )
    if review_required:
        actions.append(
            {
                "priority": "high",
                "action": "defer_full_xlsx_export",
                "reason": "When review is pending, export JSON preview first and generate XLSX after confirmation.",
            }
        )
    if config.cache_enabled:
        actions.append(
            {
                "priority": "high",
                "action": "enable_page_cache",
                "reason": "Reuse per-page results via hash-based caching to avoid full reruns.",
            }
        )
    if config.delta_execution_enabled:
        actions.append(
            {
                "priority": "high",
                "action": "enable_delta_execution",
                "reason": "Run pricing-only or Factor-F-only updates without re-extracting geometry.",
            }
        )
    if not config.vision_enabled:
        actions.append(
            {
                "priority": "high",
                "action": "disable_heavy_vision_by_default",
                "reason": "Heavy vision is optional and should only run on approval or cache miss.",
            }
        )
    if config.vision_requires_approval:
        actions.append(
            {
                "priority": "high",
                "action": "require_vision_approval",
                "reason": "Vision inference requires explicit approval when cheaper paths fail.",
            }
        )
    if config.riser_mode == "manual":
        actions.append(
            {
                "priority": "medium",
                "action": "manual_riser_input",
                "reason": "Use manual riser inputs for low-cost MEP runs instead of auto inference.",
            }
        )
    actions.extend(
        [
            {
                "priority": "medium",
                "action": "reuse_project_defaults",
                "reason": "Use configured heights and waste presets before expensive inference.",
            },
            {
                "priority": "medium",
                "action": "price_late",
                "reason": "Generate PO-5 and PO-6 only after PO-4 quantities stabilize.",
            },
            {
                "priority": "medium",
                "action": "review_only_low_confidence",
                "reason": "Route only sub-0.95 detections to manual review instead of reprocessing all pages.",
            },
        ]
    )

    estimated_profile = "low"
    if tiers["high"] > 0:
        estimated_profile = "medium" if tiers["low"] > 0 else "high"
    elif tiers["medium"] > 0:
        estimated_profile = "medium"

    return {
        "mode": "smart_low_cost",
        "estimated_cost_profile": estimated_profile,
        "source_mix": dict(tiers),
        "actions": actions,
        "cache": {
            "enabled": config.cache_enabled,
            "policy": config.cache_policy,
            "key_fields": ["file_hash", "page_index", "scale_ratio"],
        },
        "delta_execution": {
            "enabled": config.delta_execution_enabled,
            "paths": ["price_only", "factor_f_only", "vision_only"],
        },
        "guardrails": {
            "ocr_page_cap_pct": config.ocr_page_cap_pct,
            "vision_page_cap_pct": config.vision_page_cap_pct,
            "storage_cap_mb": config.storage_cap_mb,
            "runtime_cap_minutes": config.runtime_cap_minutes,
            "parity_gate_pct": config.parity_gate_pct,
        },
        "vision": {
            "enabled": config.vision_enabled,
            "requires_approval": config.vision_requires_approval,
            "approved": config.vision_approved,
        },
        "riser_mode": config.riser_mode,
        "expected_savings": [
            "Reduce OCR usage by preferring vector CAD/PDF paths",
            "Delay workbook generation until review blockers are cleared",
            "Minimize manual review scope to low-confidence detections only",
            "Reuse cached pages and delta updates instead of full reprocessing",
        ],
    }
