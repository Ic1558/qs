from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any, Dict, List, Optional


def to_data(value: Any) -> Any:
    if is_dataclass(value):
        return {key: to_data(val) for key, val in asdict(value).items()}
    if isinstance(value, list):
        return [to_data(item) for item in value]
    if isinstance(value, dict):
        return {key: to_data(val) for key, val in value.items()}
    return value


@dataclass(slots=True)
class SourceSpec:
    path: str
    format: str
    discipline: str
    vector_pdf: Optional[bool] = None


@dataclass(slots=True)
class ProjectConfig:
    project_name: str
    unit_system: str
    floor_to_floor_height_m: float
    pdf_scale_ratio: Optional[float]
    waste_factors: Dict[str, float]
    vat_enabled: bool
    factor_f_enabled: bool
    factor_f_table: str
    low_cost_mode: bool = True
    ocr_page_cap_pct: float = 0.15
    vision_page_cap_pct: float = 0.05
    storage_cap_mb: float = 200.0
    runtime_cap_minutes: float = 8.0
    parity_gate_pct: float = 2.0
    vision_enabled: bool = False
    vision_requires_approval: bool = True
    vision_approved: bool = False
    riser_mode: str = "manual"
    manual_riser_count: int = 0
    cache_enabled: bool = True
    cache_policy: str = "hash_page"
    delta_execution_enabled: bool = True


@dataclass(slots=True)
class TakeoffRequest:
    job_id: str
    sources: List[SourceSpec]
    config: ProjectConfig

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "TakeoffRequest":
        sources = [SourceSpec(**item) for item in payload.get("sources", [])]
        config = ProjectConfig(**payload["config"])
        return cls(job_id=payload["job_id"], sources=sources, config=config)


@dataclass(slots=True)
class AuditLink:
    source_file: str
    discipline: str
    locator: str


@dataclass(slots=True)
class ReviewItem:
    code: str
    severity: str
    message: str
    source_file: str


@dataclass(slots=True)
class ElementRecord:
    id: str
    discipline: str
    category: str
    unit: str
    quantity: float
    formula: str
    proof: Dict[str, Any]
    audit_link: AuditLink
    confidence: float
    sub_items: List[Dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class WorkbookPlan:
    filename: str
    tabs: List[str]
    notes: List[str]
    template: Dict[str, Any]


@dataclass(slots=True)
class PreviewResult:
    schema_version: str
    job_id: str
    project_name: str
    status: str
    supported_formats: List[str]
    stages: List[Dict[str, str]]
    elements: List[ElementRecord]
    review_queue: List[ReviewItem]
    workbook: WorkbookPlan
    fallback_rules: List[Dict[str, Any]]
    acceptance_gate: Dict[str, Any]
    optimization_plan: Dict[str, Any]
    integration: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return to_data(self)
