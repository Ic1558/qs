from __future__ import annotations

from dataclasses import dataclass


ALLOWED_STATES: tuple[str, ...] = (
    "submitted",
    "queued",
    "running",
    "blocked_approval",
    "completed",
    "failed",
    "rejected",
)


class UnknownJobContractError(KeyError):
    """Raised when a caller asks for a job contract that is not defined."""


@dataclass(frozen=True, slots=True)
class JobContract:
    job_type: str
    inputs: tuple[str, ...]
    expected_outputs: tuple[str, ...]
    requires_approval: bool
    allowed_states: tuple[str, ...]


_CONTRACTS: dict[str, JobContract] = {
    "qs.boq_generate": JobContract(
        job_type="qs.boq_generate",
        inputs=("project_id", "source_refs", "config_snapshot", "output_mode"),
        expected_outputs=("boq_json", "internal_trace_xlsx", "run_manifest"),
        requires_approval=False,
        allowed_states=ALLOWED_STATES,
    ),
    "qs.compliance_check": JobContract(
        job_type="qs.compliance_check",
        inputs=("project_id", "run_ref", "acceptance_snapshot", "review_queue"),
        expected_outputs=("compliance_report_json", "gate_summary", "run_manifest"),
        requires_approval=False,
        allowed_states=ALLOWED_STATES,
    ),
    "qs.po_generate": JobContract(
        job_type="qs.po_generate",
        inputs=("project_id", "estimate_ref", "package_scope", "vendor_context"),
        expected_outputs=("po_package", "po_manifest", "run_manifest"),
        requires_approval=True,
        allowed_states=ALLOWED_STATES,
    ),
    "qs.report_export": JobContract(
        job_type="qs.report_export",
        inputs=("project_id", "run_ref", "report_type", "delivery_format"),
        expected_outputs=("summary_report", "export_bundle", "run_manifest"),
        requires_approval=False,
        allowed_states=ALLOWED_STATES,
    ),
}


def list_job_contracts() -> tuple[JobContract, ...]:
    return tuple(_CONTRACTS[key] for key in sorted(_CONTRACTS))


def get_job_contract(job_type: str) -> JobContract:
    try:
        return _CONTRACTS[job_type]
    except KeyError as exc:
        raise UnknownJobContractError(f"unknown_job_type:{job_type}") from exc
