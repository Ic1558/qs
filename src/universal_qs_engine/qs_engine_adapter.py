from __future__ import annotations

from pathlib import Path
import sys
from typing import Any, Dict, Tuple

from .project_store import load_project


def _candidate_tool_roots() -> list[Path]:
    here = Path(__file__).resolve()
    candidates: list[Path] = []
    for parent in here.parents:
        tool_root = parent / "tools"
        if (tool_root / "qs_engine" / "__init__.py").exists():
            candidates.append(tool_root)
    env_root = Path("/Users/icmini/0luka/tools")
    if (env_root / "qs_engine" / "__init__.py").exists():
        candidates.append(env_root)
    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return unique


def _load_qs_engine() -> tuple[Any, Any, Any, Any]:
    try:
        from qs_engine.calc_engine import run as calc_run
        from qs_engine.compliance import run_all
        from qs_engine.contracts import ElementRecord, ProjectConfig
        from qs_engine.po_writer import write_workbook
        return calc_run, run_all, ElementRecord, ProjectConfig, write_workbook
    except ModuleNotFoundError:
        for tool_root in _candidate_tool_roots():
            if str(tool_root) not in sys.path:
                sys.path.insert(0, str(tool_root))
            try:
                from qs_engine.calc_engine import run as calc_run
                from qs_engine.compliance import run_all
                from qs_engine.contracts import ElementRecord, ProjectConfig
                from qs_engine.po_writer import write_workbook
                return calc_run, run_all, ElementRecord, ProjectConfig, write_workbook
            except ModuleNotFoundError:
                continue
    raise ModuleNotFoundError(
        "qs_engine is not installed. Install or expose tools/qs_engine before export."
    )


def _rate_lookup(project: Dict[str, Any], boq_line: Dict[str, Any]) -> Dict[str, float]:
    if float(boq_line.get("mat_rate", 0.0)) or float(boq_line.get("lab_rate", 0.0)):
        return {
            "mat_rate": float(boq_line.get("mat_rate", 0.0)),
            "lab_rate": float(boq_line.get("lab_rate", 0.0)),
        }
    rate_context = boq_line.get("rate_context", "new")
    description = boq_line.get("description", "")
    component_type = boq_line.get("category", "")
    for rate in project.get("rates", []):
        if rate.get("rate_context") != rate_context:
            continue
        if rate.get("item_code") in description or rate.get("item_code") == component_type:
            return {
                "mat_rate": float(rate.get("material_rate", 0.0)),
                "lab_rate": float(rate.get("labor_rate", 0.0)),
            }
    return {"mat_rate": 0.0, "lab_rate": 0.0}


def _to_engine_payload(project: Dict[str, Any], *, element_record_cls: Any, project_config_cls: Any) -> Tuple[Any, list[Any]]:
    project_raw = project["project"]
    config = project_config_cls(
        name=project_raw.get("name", "Untitled QS Project"),
        type=project_raw.get("project_type", "main"),
        date=project.get("updated_at", ""),
        owner=project_raw.get("client", ""),
        site=project_raw.get("site", ""),
        factor_f_mode=project_raw.get("factor_mode", "private"),
        overhead_rate=float(project_raw.get("overhead_rate", 0.12)),
        vat_enabled=bool(project_raw.get("vat_enabled", False)),
        currency=project_raw.get("currency", "THB"),
    )

    elements: list[Any] = []
    for line in project.get("calc_graph", {}).get("boq_lines", []):
        rates = _rate_lookup(project, line)
        elements.append(
            element_record_cls(
                code=line.get("boq_code") or line.get("boq_line_id", ""),
                desc=line.get("description", ""),
                category=line.get("category", "Other"),
                unit=line.get("unit", ""),
                qty=float(line.get("qty", 0.0)),
                mat_rate=rates["mat_rate"],
                lab_rate=rates["lab_rate"],
                waste_pct=0.0,
                type=line.get("line_type", "ADD"),
                source_ref=line.get("source_ref", ""),
                note=line.get("basis_status", ""),
                abt_charged_override=line.get("abt_charged_override"),
            )
        )
    return config, elements


def export_project_to_xlsx(project_id: str, output_path: str) -> Dict[str, Any]:
    calc_run, run_all, element_record_cls, project_config_cls, write_workbook = _load_qs_engine()
    project = load_project(project_id)
    config, elements = _to_engine_payload(project, element_record_cls=element_record_cls, project_config_cls=project_config_cls)
    result = calc_run(config, elements)
    result = run_all(result)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    write_workbook(result, output_path)
    return {
        "D": result.D,
        "F": result.F,
        "contract_amt": result.contract_amt,
        "final_bid": result.final_bid,
        "review_queue": result.review_queue,
        "output_path": output_path,
    }
