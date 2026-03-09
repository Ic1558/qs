from __future__ import annotations

import importlib
import os
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

import yaml

from universal_qs_engine.queue_transport import build_queue_result_message
from universal_qs_engine.result_envelope import build_result_envelope
from universal_qs_engine.run_manifest import create_run_manifest, transition_status
from universal_qs_engine.runtime_transport_adapter import build_runtime_transport_payload
from universal_qs_engine.zero_luka_bridge_adapter import build_0luka_bridge_payload
from universal_qs_engine.zero_luka_live_ingress import (
    ZeroLukaLiveIngressError,
    build_0luka_ingress_task,
    submit_0luka_bridge_payload,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))


def _set_env(root: Path) -> dict[str, str | None]:
    old = {
        "ROOT": os.environ.get("ROOT"),
        "0LUKA_ROOT": os.environ.get("0LUKA_ROOT"),
        "LUKA_RUNTIME_ROOT": os.environ.get("LUKA_RUNTIME_ROOT"),
    }
    os.environ["ROOT"] = str(root)
    os.environ["0LUKA_ROOT"] = str(root)
    os.environ["LUKA_RUNTIME_ROOT"] = str(root / "runtime_state")
    return old


def _restore_env(old: dict[str, str | None]) -> None:
    for key, val in old.items():
        if val is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = val


def _setup_dirs(root: Path) -> None:
    from core.verify._test_root import ensure_test_root

    ensure_test_root(root)
    (root / "runtime_state" / "logs").mkdir(parents=True, exist_ok=True)
    (root / "runtime_state" / "artifacts").mkdir(parents=True, exist_ok=True)
    (root / "runtime_state" / "state").mkdir(parents=True, exist_ok=True)


def _reload_core_modules() -> None:
    importlib.reload(importlib.import_module("core.config"))
    importlib.reload(importlib.import_module("core.submit"))
    importlib.reload(importlib.import_module("core.bridge"))


class ZeroLukaLiveIngressTests(unittest.TestCase):
    def _build_bridge_payload(self, job_type: str, project_id: str, status: str):
        manifest = create_run_manifest(job_type, project_id)
        manifest = transition_status(manifest, "queued")
        manifest = transition_status(manifest, "running")
        manifest = transition_status(manifest, status)
        expected_outputs = {
            "qs.boq_generate": ("boq_json", "internal_trace_xlsx", "run_manifest"),
            "qs.compliance_check": ("compliance_report_json", "gate_summary", "run_manifest"),
            "qs.po_generate": ("po_package", "po_manifest", "run_manifest"),
        }[job_type]
        kwargs = {}
        if status == "failed":
            kwargs = {"error_code": "ingress_failed", "error_message": "failed at ingress test"}
        elif status == "rejected":
            kwargs = {"error_code": "ingress_rejected", "error_message": "rejected at ingress test"}
        envelope = build_result_envelope(manifest, expected_outputs=expected_outputs, **kwargs)
        message = build_queue_result_message(envelope)
        runtime_payload = build_runtime_transport_payload(message)
        return build_0luka_bridge_payload(runtime_payload)

    def test_build_ingress_task_preserves_identity_and_status(self) -> None:
        bridge_payload = self._build_bridge_payload("qs.boq_generate", "prj_901", "completed")
        task = build_0luka_ingress_task(bridge_payload)

        self.assertEqual(task["task_id"], bridge_payload.run_id)
        self.assertEqual(task["intent"], "qs.bridge_result.ingress")
        self.assertEqual(task["inputs"]["run_id"], bridge_payload.run_id)
        self.assertEqual(task["inputs"]["job_type"], bridge_payload.job_type)
        self.assertEqual(task["inputs"]["project_id"], bridge_payload.project_id)
        self.assertEqual(task["inputs"]["status"], bridge_payload.status)

    def test_submit_completed_payload_into_real_ingress_lane(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve()
            old = _set_env(root)
            try:
                _setup_dirs(root)
                _reload_core_modules()
                bridge_payload = self._build_bridge_payload("qs.boq_generate", "prj_902", "completed")
                receipt = submit_0luka_bridge_payload(bridge_payload)

                self.assertEqual(receipt["status"], "submitted")
                inbox_file = root / receipt["inbox_path"]
                self.assertTrue(inbox_file.exists())
                data = yaml.safe_load(inbox_file.read_text(encoding="utf-8"))
                self.assertEqual(data["task_id"], bridge_payload.run_id)
                self.assertEqual(data["inputs"]["run_id"], bridge_payload.run_id)
                self.assertEqual(data["inputs"]["status"], "completed")
            finally:
                from core.verify._test_root import restore_test_root_modules

                restore_test_root_modules()
                _restore_env(old)

    def test_submit_failed_payload_into_real_ingress_lane(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve()
            old = _set_env(root)
            try:
                _setup_dirs(root)
                _reload_core_modules()
                bridge_payload = self._build_bridge_payload("qs.compliance_check", "prj_903", "failed")
                receipt = submit_0luka_bridge_payload(bridge_payload)

                self.assertEqual(receipt["status"], "submitted")
                inbox_file = root / receipt["inbox_path"]
                data = yaml.safe_load(inbox_file.read_text(encoding="utf-8"))
                self.assertEqual(data["inputs"]["run_id"], bridge_payload.run_id)
                self.assertEqual(data["inputs"]["status"], "failed")
            finally:
                from core.verify._test_root import restore_test_root_modules

                restore_test_root_modules()
                _restore_env(old)

    def test_rejects_malformed_payload_at_ingress_boundary(self) -> None:
        bridge_payload = self._build_bridge_payload("qs.po_generate", "prj_904", "rejected")
        with self.assertRaises(ZeroLukaLiveIngressError):
            submit_0luka_bridge_payload(replace(bridge_payload, run_id=""))


if __name__ == "__main__":
    unittest.main()
