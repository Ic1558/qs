from __future__ import annotations

import io
import json
import tempfile
import unittest
from email.message import Message
from pathlib import Path
from unittest.mock import patch

from universal_qs_engine import project_store
from universal_qs_engine.service import JOB_STATE, RequestHandler, build_health_payload


class _HarnessHandler(RequestHandler):
    def __init__(self, path: str, *, method: str = "GET", payload: dict | None = None) -> None:
        self.path = path
        self.command = method
        self.request_version = "HTTP/1.1"
        self.requestline = f"{method} {path} HTTP/1.1"
        self.client_address = ("127.0.0.1", 0)
        self.server = None
        self.rfile = io.BytesIO()
        self.wfile = io.BytesIO()
        self.headers = Message()
        self.status_code: int | None = None
        self.sent_headers: list[tuple[str, str]] = []
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            self.rfile = io.BytesIO(body)
            self.headers["Content-Length"] = str(len(body))
            self.headers["Content-Type"] = "application/json"

    def send_response(self, code: int, message: str | None = None) -> None:  # noqa: D401
        self.status_code = code

    def send_header(self, keyword: str, value: str) -> None:  # noqa: D401
        self.sent_headers.append((keyword, value))

    def end_headers(self) -> None:  # noqa: D401
        return

    def json_body(self) -> dict:
        return json.loads(self.wfile.getvalue().decode("utf-8"))

    def text_body(self) -> str:
        return self.wfile.getvalue().decode("utf-8")


class AuthoringApiServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        JOB_STATE.clear()
        self._tmpdir = tempfile.TemporaryDirectory()
        self.projects_dir = Path(self._tmpdir.name) / "projects"
        self.project_dir_patch = patch.object(project_store, "PROJECTS_DIR", self.projects_dir)
        self.project_dir_patch.start()

    def tearDown(self) -> None:
        self.project_dir_patch.stop()
        self._tmpdir.cleanup()

    def test_health_payload_advertises_v2_routes(self) -> None:
        payload = build_health_payload()
        self.assertIn("/api/v2/projects", payload["endpoints"])
        self.assertIn("/api/v2/projects/:id/export/owner", payload["endpoints"])

    def test_root_serves_authoring_workspace_html(self) -> None:
        handler = _HarnessHandler("/")
        handler.do_GET()
        self.assertEqual(handler.status_code, 200)
        html = handler.text_body()
        self.assertIn("QS Authoring Workspace", html)
        self.assertIn("btn-create-project", html)

    def test_v2_project_create_get_patch_and_member_round_trip(self) -> None:
        create_handler = _HarnessHandler(
            "/api/v2/projects",
            method="POST",
            payload={
                "name": "Service Project",
                "client": "IC",
                "site": "Bangkok",
                "factor_mode": "private",
            },
        )
        create_handler.do_POST()
        self.assertEqual(create_handler.status_code, 200)
        created = create_handler.json_body()
        project_id = created["project"]["project_id"]

        get_handler = _HarnessHandler(f"/api/v2/projects/{project_id}")
        get_handler.do_GET()
        self.assertEqual(get_handler.status_code, 200)
        self.assertEqual(get_handler.json_body()["project"]["project"]["name"], "Service Project")

        patch_handler = _HarnessHandler(
            f"/api/v2/projects/{project_id}",
            method="PATCH",
            payload={"site": "Chiang Mai"},
        )
        patch_handler.do_PATCH()
        self.assertEqual(patch_handler.status_code, 200)
        self.assertEqual(patch_handler.json_body()["project"]["project"]["site"], "Chiang Mai")

        member_handler = _HarnessHandler(
            f"/api/v2/projects/{project_id}/members/beam",
            method="POST",
            payload={
                "member_code": "GB1",
                "level": "GF",
                "grid_ref": "A-1 to B-1",
                "clear_span": 5.5,
                "section_width": 0.2,
                "section_depth": 0.4,
                "basis_status": "VERIFIED_DETAIL",
                "source_ref": "S-X1-307/GB1",
            },
        )
        member_handler.do_POST()
        self.assertEqual(member_handler.status_code, 200)
        self.assertEqual(member_handler.json_body()["member"]["member_type"], "beam")

        takeoff_handler = _HarnessHandler(f"/api/v2/projects/{project_id}/takeoff")
        takeoff_handler.do_GET()
        self.assertEqual(takeoff_handler.status_code, 200)
        self.assertEqual(len(takeoff_handler.json_body()["takeoff"]["members"]), 1)

        acceptance_handler = _HarnessHandler(f"/api/v2/projects/{project_id}/acceptance")
        acceptance_handler.do_GET()
        self.assertEqual(acceptance_handler.status_code, 200)
        evaluation = acceptance_handler.json_body()["evaluation"]
        self.assertIn("ok", evaluation)
        self.assertIn("criteria", evaluation)


if __name__ == "__main__":
    unittest.main()
