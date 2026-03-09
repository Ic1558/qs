from __future__ import annotations

from typing import Any

from .zero_luka_bridge_adapter import ZeroLukaBridgePayload


class ZeroLukaLiveIngressError(ValueError):
    """Raised when a bridge payload cannot be handed into the 0luka ingress lane."""


_TERMINAL_STATUSES = {"completed", "failed", "rejected"}


def build_0luka_ingress_task(bridge_payload: ZeroLukaBridgePayload) -> dict[str, Any]:
    if not isinstance(bridge_payload, ZeroLukaBridgePayload):
        raise ZeroLukaLiveIngressError("zero_luka_bridge_payload_required")
    if not bridge_payload.bridge_kind or bridge_payload.bridge_kind != "0luka.bridge_result":
        raise ZeroLukaLiveIngressError("bridge_kind_invalid")
    if not bridge_payload.run_id or not bridge_payload.run_id.strip():
        raise ZeroLukaLiveIngressError("run_id_required")
    if not bridge_payload.job_type or not bridge_payload.job_type.strip():
        raise ZeroLukaLiveIngressError("job_type_required")
    if not bridge_payload.project_id or not bridge_payload.project_id.strip():
        raise ZeroLukaLiveIngressError("project_id_required")
    if bridge_payload.status not in _TERMINAL_STATUSES:
        raise ZeroLukaLiveIngressError(f"terminal_status_required:{bridge_payload.status}")
    if not isinstance(bridge_payload.payload, dict):
        raise ZeroLukaLiveIngressError("payload_required")

    return {
        "task_id": bridge_payload.run_id,
        "author": "bridge",
        "call_sign": "[Bridge]",
        "root": "${ROOT}",
        "created_at_utc": "2026-03-09T00:00:00Z",
        "ts_utc": "2026-03-09T00:00:00Z",
        "lane": "task",
        "intent": "qs.bridge_result.ingress",
        "schema_version": "clec.v1",
        "ops": [
            {
                "op_id": "ingress_noop",
                "type": "run",
                "command": "git status",
            }
        ],
        "verify": [],
        "inputs": {
            "kind": bridge_payload.kind,
            "bridge_kind": bridge_payload.bridge_kind,
            "run_id": bridge_payload.run_id,
            "job_type": bridge_payload.job_type,
            "project_id": bridge_payload.project_id,
            "status": bridge_payload.status,
            "payload": bridge_payload.payload,
        },
    }


def submit_0luka_bridge_payload(bridge_payload: ZeroLukaBridgePayload) -> dict[str, Any]:
    task = build_0luka_ingress_task(bridge_payload)
    try:
        from core.bridge import BridgeError, submit_bridge_task
    except Exception as exc:
        raise ZeroLukaLiveIngressError(f"bridge_runtime_unavailable:{exc}") from exc

    try:
        return submit_bridge_task(task, task_id=bridge_payload.run_id)
    except BridgeError as exc:
        raise ZeroLukaLiveIngressError(str(exc)) from exc
