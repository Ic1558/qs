from __future__ import annotations

from typing import Any, Callable

from .job_context import canonical_job_type, normalize_job_context
from .job_output import normalize_job_output
from .jobs import (
    run_boq_extract,
    run_cost_estimate,
    run_po_generate,
    run_report_generate,
)

JobHandler = Callable[[dict[str, Any]], dict[str, Any]]


class UnknownQSJobError(KeyError):
    """Raised when a QS job type is not registered."""


JOB_REGISTRY: dict[str, JobHandler] = {
    "qs.boq_extract": run_boq_extract,
    "qs.boq_generate": run_boq_extract,
    "qs.cost_estimate": run_cost_estimate,
    "qs.po_generate": run_po_generate,
    "qs.report_generate": run_report_generate,
    "qs.report_export": run_report_generate,
}


def get_job_handler(job_type: str) -> JobHandler:
    try:
        return JOB_REGISTRY[job_type]
    except KeyError as exc:
        raise UnknownQSJobError(f"unknown_qs_job_type:{job_type}") from exc


def run_registered_job(job_type: str, context: dict[str, Any]) -> dict[str, Any]:
    canonical_type = canonical_job_type(job_type)
    handler = get_job_handler(job_type)
    normalized_context = normalize_job_context(canonical_type, context)
    raw_output = handler(normalized_context)
    return normalize_job_output(canonical_type, raw_output)
