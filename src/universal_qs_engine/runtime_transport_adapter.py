from __future__ import annotations

from dataclasses import dataclass

from .queue_transport import QueueResultMessage


class RuntimeTransportAdapterError(ValueError):
    """Raised when a queue result message cannot be translated to runtime transport payload."""


@dataclass(frozen=True, slots=True)
class RuntimeTransportPayload:
    kind: str
    run_id: str
    job_type: str
    project_id: str
    status: str
    body: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "run_id": self.run_id,
            "job_type": self.job_type,
            "project_id": self.project_id,
            "status": self.status,
            "body": dict(self.body),
        }


def build_runtime_transport_payload(message: QueueResultMessage) -> RuntimeTransportPayload:
    if not isinstance(message, QueueResultMessage):
        raise RuntimeTransportAdapterError("queue_result_message_required")
    if not message.run_id or not message.run_id.strip():
        raise RuntimeTransportAdapterError("run_id_required")
    if not message.job_type or not message.job_type.strip():
        raise RuntimeTransportAdapterError("job_type_required")
    if not message.project_id or not message.project_id.strip():
        raise RuntimeTransportAdapterError("project_id_required")
    if not message.status or not message.status.strip():
        raise RuntimeTransportAdapterError("status_required")
    if not isinstance(message.envelope_payload, dict):
        raise RuntimeTransportAdapterError("envelope_payload_required")

    return RuntimeTransportPayload(
        kind="qs.runtime_result",
        run_id=message.run_id,
        job_type=message.job_type,
        project_id=message.project_id,
        status=message.status,
        body=message.to_dict(),
    )
