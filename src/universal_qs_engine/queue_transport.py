from __future__ import annotations

from dataclasses import dataclass

from .result_envelope import ResultEnvelope


class QueueTransportError(ValueError):
    """Raised when a result envelope cannot be projected into a transport payload."""


@dataclass(frozen=True, slots=True)
class QueueResultMessage:
    run_id: str
    job_type: str
    project_id: str
    status: str
    outcome_classification: str
    requires_approval: bool
    envelope_payload: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "job_type": self.job_type,
            "project_id": self.project_id,
            "status": self.status,
            "outcome_classification": self.outcome_classification,
            "requires_approval": self.requires_approval,
            "envelope_payload": dict(self.envelope_payload),
        }


def build_queue_result_message(envelope: ResultEnvelope) -> QueueResultMessage:
    if not isinstance(envelope, ResultEnvelope):
        raise QueueTransportError("result_envelope_required")
    if not envelope.run_id or not envelope.run_id.strip():
        raise QueueTransportError("run_id_required")
    if not envelope.job_type or not envelope.job_type.strip():
        raise QueueTransportError("job_type_required")
    if not envelope.project_id or not envelope.project_id.strip():
        raise QueueTransportError("project_id_required")
    if not envelope.status or not envelope.status.strip():
        raise QueueTransportError("status_required")
    if not envelope.outcome_classification or not envelope.outcome_classification.strip():
        raise QueueTransportError("outcome_classification_required")

    return QueueResultMessage(
        run_id=envelope.run_id,
        job_type=envelope.job_type,
        project_id=envelope.project_id,
        status=envelope.status,
        outcome_classification=envelope.outcome_classification,
        requires_approval=envelope.requires_approval,
        envelope_payload=envelope.to_dict(),
    )
