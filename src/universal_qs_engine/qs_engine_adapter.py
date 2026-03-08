from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import sys
from typing import Any, Dict, Tuple

from .project_store import load_project


@lru_cache(maxsize=1)
def _load_qs_engine() -> Dict[str, Any]:
    def _try_import():
        from qs_engine.calc_engine import run as calc_run
        from qs_engine.compliance import run_all
        from qs_engine.contracts import ElementRecord, ProjectConfig
        from qs_engine.po_writer import write_workbook
        return {
            "calc_run": calc_run,
            "run_all": run_all,
            "ElementRecord": ElementRecord,
            "ProjectConfig": ProjectConfig,
            "write_workbook": write_workbook,
        }

    try:
        return _try_import()
    except ModuleNotFoundError:
        tools_root = Path(__file__).resolve().parents[4] / "tools"
        if str(tools_root) not in sys.path:
            sys.path.insert(0, str(tools_root))
        try:
            return _try_import()
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(
                "qs_engine is not installed. Install /Users/icmini/0luka/tools/qs_engine first."
            ) from exc


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


def _to_engine_payload(project: Dict[str, Any], engine: Dict[str, Any]) -> Tuple[Any, list]:
    ProjectConfig = engine["ProjectConfig"]
    ElementRecord = engine["ElementRecord"]
    project_raw = project["project"]
    config = ProjectConfig(
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

    elements: list[ElementRecord] = []
    for line in project.get("calc_graph", {}).get("boq_lines", []):
        rates = _rate_lookup(project, line)
        elements.append(
            ElementRecord(
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
    engine = _load_qs_engine()
    project = load_project(project_id)
    config, elements = _to_engine_payload(project, engine)
    result = engine["calc_run"](config, elements)
    result = engine["run_all"](result)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    engine["write_workbook"](result, output_path)
    return {
        "D": result.D,
        "F": result.F,
        "contract_amt": result.contract_amt,
        "final_bid": result.final_bid,
        "review_queue": result.review_queue,
        "output_path": output_path,
    }
