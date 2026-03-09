from __future__ import annotations

from dataclasses import dataclass

from .runtime_transport_adapter import RuntimeTransportPayload


class ZeroLukaBridgeAdapterError(ValueError):
    """Raised when a runtime transport payload cannot be translated to a 0luka bridge payload."""


@dataclass(frozen=True, slots=True)
class ZeroLukaBridgePayload:
    kind: str
    bridge_kind: str
    run_id: str
    job_type: str
    project_id: str
    status: str
    payload: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "bridge_kind": self.bridge_kind,
            "run_id": self.run_id,
            "job_type": self.job_type,
            "project_id": self.project_id,
            "status": self.status,
            "payload": dict(self.payload),
        }


def build_0luka_bridge_payload(runtime_payload: RuntimeTransportPayload) -> ZeroLukaBridgePayload:
    if not isinstance(runtime_payload, RuntimeTransportPayload):
        raise ZeroLukaBridgeAdapterError("runtime_transport_payload_required")
    if not runtime_payload.kind or not runtime_payload.kind.strip():
        raise ZeroLukaBridgeAdapterError("kind_required")
    if not runtime_payload.run_id or not runtime_payload.run_id.strip():
        raise ZeroLukaBridgeAdapterError("run_id_required")
    if not runtime_payload.job_type or not runtime_payload.job_type.strip():
        raise ZeroLukaBridgeAdapterError("job_type_required")
    if not runtime_payload.project_id or not runtime_payload.project_id.strip():
        raise ZeroLukaBridgeAdapterError("project_id_required")
    if not runtime_payload.status or not runtime_payload.status.strip():
        raise ZeroLukaBridgeAdapterError("status_required")
    if not isinstance(runtime_payload.body, dict):
        raise ZeroLukaBridgeAdapterError("payload_body_required")

    return ZeroLukaBridgePayload(
        kind=runtime_payload.kind,
        bridge_kind="0luka.bridge_result",
        run_id=runtime_payload.run_id,
        job_type=runtime_payload.job_type,
        project_id=runtime_payload.project_id,
        status=runtime_payload.status,
        payload=runtime_payload.to_dict(),
    )
