from __future__ import annotations

import math
from typing import Any, Dict, List

import pdfplumber

def _scaled_length(value: float, scale_factor: float) -> float:
    return float(round(float(value) * scale_factor, 3))

def _scaled_area(value: float, scale_factor: float) -> float:
    return float(round(float(value) * (scale_factor ** 2), 3))

def _mark_review_required(entity: Dict[str, Any], reason: str) -> None:
    entity["review_required"] = True
    entity["review_reason"] = reason

def extract_pdf_entities(file_path: str, scale_factor: float) -> Dict[str, Any]:
    """
    Extracts native vector entities (lines, rects, curves) from a PDF if present.
    In a Vector-First Low-Cost engine, we rely on these primitives before OCR/Vision.
    """
    results: List[Dict[str, Any]] = []
    review_queue: List[Dict[str, Any]] = []
    metrics = {
        "extractor": "pdfplumber",
        "scale_factor_m_per_unit": scale_factor,
        "total_entities": 0,
        "kept_entities": 0,
        "generic_entities": 0,
        "geometry_measured_entities": 0,
        "review_required_entities": 0,
        "vector_pages": 0,
        "raster_pages": 0,
    }

    try:
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                page_lines = page.lines
                page_rects = page.rects
                page_curves = page.curves
                
                total_page_vectors = len(page_lines) + len(page_rects) + len(page_curves)
                if total_page_vectors > 50:
                    metrics["vector_pages"] += 1
                else:
                    metrics["raster_pages"] += 1
                    # A raster page primarily relies on scanned images. This requires Vision fallback.

                for line in page_lines:
                    metrics["total_entities"] += 1
                    MetricsLen = math.sqrt(line.get("width", 0)**2 + line.get("height", 0)**2)
                    
                    if MetricsLen < 1.0: # Filter out extremely small noise points
                        continue
                        
                    ent_data = {
                        "id": f"pdf_l_{page_num}_{metrics['total_entities']}",
                        "page": page_num,
                        "type": "line",
                        "discipline": "generic",
                        "category": "generic",
                        "length_m": _scaled_length(MetricsLen, scale_factor)
                    }
                    metrics["geometry_measured_entities"] += 1
                    metrics["generic_entities"] += 1
                    results.append(ent_data)

                for rect in page_rects:
                    metrics["total_entities"] += 1
                    w = rect.get("width", 0)
                    h = rect.get("height", 0)
                    
                    if w < 1.0 and h < 1.0:
                        continue
                        
                    ent_data = {
                        "id": f"pdf_r_{page_num}_{metrics['total_entities']}",
                        "page": page_num,
                        "type": "rect",
                        "discipline": "generic",
                        "category": "generic",
                        "area_m2": _scaled_area(w * h, scale_factor),
                        "length_m": _scaled_length(2 * (w + h), scale_factor)
                    }
                    metrics["geometry_measured_entities"] += 1
                    metrics["generic_entities"] += 1
                    results.append(ent_data)
                    
    except Exception as e:
        raise ValueError(f"Failed to read Vector PDF file: {e}")

    # For PDFs, since we don't have CAD layer names, almost everything is generic
    # in Phase 1 MVP. We queue a small subset of largest shapes for Review as an example.
    
    # Sort by area descending to find the top biggest shapes to review (just as a mock fallback mechanism)
    rects = [e for e in results if e["type"] == "rect"]
    rects.sort(key=lambda x: x.get("area_m2", 0), reverse=True)
    
    for r in rects[:10]: # Flag top 10 largest rectangles (might be rooms or slabs)
        _mark_review_required(r, "unclassified_large_area")
        metrics["review_required_entities"] += 1
        review_queue.append({
            "entity_id": r["id"],
            "page": r["page"],
            "type": r["type"],
            "reason": r["review_reason"]
        })

    metrics["kept_entities"] = len(results)
    
    return {
        "entities": results,
        "metrics": metrics,
        "review_queue": review_queue,
    }
