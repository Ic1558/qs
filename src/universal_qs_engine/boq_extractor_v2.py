from __future__ import annotations

from pathlib import Path
from typing import Any

from .errors import QSJobError
from .extractor_dxf import extract_dxf_entities
from .extractor_pdf import extract_pdf_entities


def _normalized_quantity(entity: dict[str, Any]) -> dict[str, Any]:
    quantity: dict[str, Any] = {
        "entity_id": str(entity.get("id") or "").strip(),
        "discipline": str(entity.get("discipline") or "generic").strip() or "generic",
        "category": str(entity.get("category") or "generic").strip() or "generic",
        "measurements": {},
    }
    measurements = quantity["measurements"]
    if "length_m" in entity:
        measurements["length_m"] = float(entity["length_m"])
    if "area_m2" in entity:
        measurements["area_m2"] = float(entity["area_m2"])
    return quantity


def extract_boq_v2(*, source_ref: str, measurement_system: str = "metric") -> dict[str, Any]:
    normalized_source = str(source_ref or "").strip()
    if not normalized_source:
        raise QSJobError("invalid_boq_source:missing_source_ref")
    if measurement_system != "metric":
        raise QSJobError(f"invalid_boq_measurement_system:{measurement_system}")

    source_path = Path(normalized_source)
    suffix = source_path.suffix.lower()
    if suffix == ".dxf":
        raw = extract_dxf_entities(str(source_path))
        source_kind = "dxf"
    elif suffix == ".pdf":
        raw = extract_pdf_entities(str(source_path), scale_factor=1.0)
        source_kind = "pdf"
    else:
        raise QSJobError(f"invalid_boq_source:unsupported_suffix:{suffix or 'missing'}")

    entities = raw.get("entities")
    metrics = raw.get("metrics")
    review_queue = raw.get("review_queue")
    if not isinstance(entities, list) or not isinstance(metrics, dict) or not isinstance(review_queue, list):
        raise QSJobError("invalid_boq_source:extractor_payload_invalid")

    normalized_quantities = [_normalized_quantity(entity) for entity in entities]
    normalized_quantities.sort(
        key=lambda item: (
            str(item["discipline"]),
            str(item["category"]),
            str(item["entity_id"]),
        )
    )
    return {
        "source_kind": source_kind,
        "measurement_system": measurement_system,
        "quantity_schema_version": "qs.boq_extract.v2",
        "metrics": metrics,
        "review_queue": review_queue,
        "normalized_quantities": normalized_quantities,
    }
