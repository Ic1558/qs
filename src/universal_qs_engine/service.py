from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from email import message_from_bytes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Tuple

from .api import (
    acceptance_evaluate,
    boq_generate,
    export_xlsx,
    extract_dwg,
    extract_pdf,
    intake_prepare,
    logic_compute,
    map_schema,
    optimize_plan,
    project_acceptance_get,
    project_acceptance_override,
    project_aggregate,
    project_calc_rebuild,
    project_component_candidates_add,
    project_component_candidates_confirm,
    project_component_candidates_get,
    project_component_candidates_reject,
    project_components_add,
    project_create,
    project_export_internal,
    project_export_owner,
    project_get,
    project_import_drawing,
    project_members_add,
    project_members_add_typed,
    project_patch,
    project_rates_add,
    project_review_get,
    project_review_ack,
    project_review_override,
    project_segments_add,
    project_sources_add,
    project_takeoff_get,
)
from .artifacts import DEFAULT_OUTPUT_DIR
from .contracts import TakeoffRequest
from .pipeline import SUPPORTED_FORMATS, build_preview_result


JOB_STATE: Dict[str, Dict[str, Any]] = {}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_health_payload() -> Dict[str, Any]:
    return {
        "status": "ok",
        "service": "universal_qs_engine",
        "ts_utc": _utc_now(),
        "supported_formats": SUPPORTED_FORMATS,
        "endpoints": [
            "/api/health",
            "/api/v2/projects",
            "/api/v2/projects/:id",
            "/api/v2/projects/:id/sources",
            "/api/v2/projects/:id/members",
            "/api/v2/projects/:id/members/:type",
            "/api/v2/projects/:id/segments",
            "/api/v2/projects/:id/components",
            "/api/v2/projects/:id/candidates/components",
            "/api/v2/projects/:id/candidates/components/:candidate_id/confirm",
            "/api/v2/projects/:id/candidates/components/:candidate_id/reject",
            "/api/v2/projects/:id/takeoff",
            "/api/v2/projects/:id/rates",
            "/api/v2/projects/:id/review",
            "/api/v2/projects/:id/review/ack",
            "/api/v2/projects/:id/review/override",
            "/api/v2/projects/:id/acceptance",
            "/api/v2/projects/:id/acceptance/override",
            "/api/v2/projects/:id/import/drawing",
            "/api/v2/projects/:id/calc-graph/rebuild",
            "/api/v2/projects/:id/export/internal",
            "/api/v2/projects/:id/export/owner",
            "/api/v1/takeoff/preview",
            "/api/v1/intake/prepare",
            "/api/v1/intake/upload",
            "/api/v1/extract/dwg",
            "/api/v1/extract/pdf",
            "/api/v1/map/schema",
            "/api/v1/logic/compute",
            "/api/v1/boq/generate",
            "/api/v1/export/xlsx",
            "/api/v1/acceptance/evaluate",
            "/api/v1/optimize/plan",
        ],
    }


def preview_from_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    request = TakeoffRequest.from_dict(payload)
    return build_preview_result(request).to_dict()


def preview_from_bytes(payload: bytes) -> Tuple[int, Dict[str, Any]]:
    try:
        body = json.loads(payload.decode("utf-8"))
        return 200, preview_from_payload(body)
    except KeyError as exc:
        return 400, {"error": f"missing field: {exc.args[0]}"}
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        return 400, {"error": str(exc)}


class RequestHandler(BaseHTTPRequestHandler):
    server_version = "UniversalQSEngine/0.1"
    routes = {
        "/api/v1/intake/prepare": intake_prepare,
        "/api/v1/extract/dwg": extract_dwg,
        "/api/v1/extract/pdf": extract_pdf,
        "/api/v1/map/schema": map_schema,
        "/api/v1/logic/compute": logic_compute,
        "/api/v1/boq/generate": boq_generate,
        "/api/v1/export/xlsx": export_xlsx,
        "/api/v1/acceptance/evaluate": acceptance_evaluate,
        "/api/v1/optimize/plan": optimize_plan,
    }

    def _send_json(self, status_code: int, payload: Dict[str, Any]) -> None:
        encoded = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _split_path(self) -> list[str]:
        path = self.path.split("?")[0].strip("/")
        return [part for part in path.split("/") if part]

    def _handle_v2_get(self) -> bool:
        parts = self._split_path()
        if parts[:2] != ["api", "v2"]:
            return False
        if parts == ["api", "v2", "projects"]:
            self._send_json(400, {"ok": False, "error": {"code": "project_id_required", "message": "Use /api/v2/projects/:id"}})
            return True
        if len(parts) >= 4 and parts[2] == "projects":
            project_id = parts[3]
            if len(parts) == 4:
                status, payload = project_get(project_id)
            elif len(parts) == 5 and parts[4] == "takeoff":
                status, payload = project_takeoff_get(project_id)
            elif len(parts) == 6 and parts[4] == "candidates" and parts[5] == "components":
                status, payload = project_component_candidates_get(project_id)
            elif len(parts) == 5 and parts[4] == "review":
                status, payload = project_review_get(project_id)
            elif len(parts) == 5 and parts[4] == "acceptance":
                status, payload = project_acceptance_get(project_id)
            else:
                self._send_json(404, {"error": "not found"})
                return True
            self._send_json(status, payload)
            return True
        return False

    def _job_state(self, job_id: str) -> Dict[str, Any]:
        return JOB_STATE.setdefault(job_id, {})

    def _resolve_uploaded_file(self, payload_data: Dict[str, Any]) -> Dict[str, Any]:
        job_id = payload_data.get("job_id")
        file_name = payload_data.get("file")
        if not job_id or not file_name:
            return payload_data
        uploads = self._job_state(str(job_id)).get("uploads", {})
        resolved = uploads.get(file_name)
        if resolved:
            payload_data = dict(payload_data)
            payload_data["file"] = resolved
        return payload_data

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/api/health":
            self._send_json(200, build_health_payload())
            return
        if self._handle_v2_get():
            return
        
        # Serve static UI files
        ui_dir = Path(__file__).parent / "ui"
        request_path = self.path.split("?")[0]
        if request_path.startswith("/outputs/"):
            target = (DEFAULT_OUTPUT_DIR / request_path.removeprefix("/outputs/")).resolve()
            if not str(target).startswith(str(DEFAULT_OUTPUT_DIR.resolve())):
                self._send_json(403, {"error": "forbidden"})
                return
            if target.is_file():
                ext = target.suffix.lower()
                mime = "application/octet-stream"
                if ext == ".xlsx":
                    mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                elif ext == ".json":
                    mime = "application/json"
                with open(target, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Content-Disposition", f'attachment; filename="{target.name}"')
                self.end_headers()
                self.wfile.write(content)
                return
            self._send_json(404, {"error": "not found"})
            return
        if request_path == "/":
            target = ui_dir / "index.html"
        else:
            target = (ui_dir / request_path.lstrip("/")).resolve()
            # Prevent directory traversal
            if not str(target).startswith(str(ui_dir.resolve())):
                self._send_json(403, {"error": "forbidden"})
                return

        if target.is_file():
            ext = target.suffix.lower()
            mime = "text/html"
            if ext == ".css":
                mime = "text/css"
            elif ext == ".js":
                mime = "application/javascript"
            
            with open(target, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        self._send_json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        parts = self._split_path()
        if parts[:2] == ["api", "v2"]:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length) if length else b"{}"
            try:
                payload_data = json.loads(body.decode("utf-8")) if body else {}
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                self._send_json(400, {"ok": False, "error": {"code": "invalid_json", "message": str(exc)}})
                return

            if parts == ["api", "v2", "projects"]:
                status, payload = project_create(payload_data)
                self._send_json(status, payload)
                return
            if len(parts) >= 5 and parts[2] == "projects":
                project_id = parts[3]
                tail = parts[4:]
                if tail == ["sources"]:
                    status, payload = project_sources_add(project_id, payload_data)
                elif tail == ["members"]:
                    status, payload = project_members_add(project_id, payload_data)
                elif len(tail) == 2 and tail[0] == "members":
                    status, payload = project_members_add_typed(project_id, tail[1], payload_data)
                elif tail == ["segments"]:
                    status, payload = project_segments_add(project_id, payload_data)
                elif tail == ["components"]:
                    status, payload = project_components_add(project_id, payload_data)
                elif tail == ["candidates", "components"]:
                    status, payload = project_component_candidates_add(project_id, payload_data)
                elif len(tail) == 4 and tail[:2] == ["candidates", "components"] and tail[3] == "confirm":
                    status, payload = project_component_candidates_confirm(project_id, tail[2], payload_data)
                elif len(tail) == 4 and tail[:2] == ["candidates", "components"] and tail[3] == "reject":
                    status, payload = project_component_candidates_reject(project_id, tail[2], payload_data)
                elif tail == ["rates"]:
                    status, payload = project_rates_add(project_id, payload_data)
                elif tail == ["review", "ack"]:
                    status, payload = project_review_ack(project_id, payload_data)
                elif tail == ["review", "override"]:
                    status, payload = project_review_override(project_id, payload_data)
                elif tail == ["acceptance", "override"]:
                    status, payload = project_acceptance_override(project_id, payload_data)
                elif tail == ["aggregate"]:
                    status, payload = project_aggregate(project_id)
                elif tail == ["import", "drawing"]:
                    status, payload = project_import_drawing(project_id, payload_data)
                elif tail == ["calc-graph", "rebuild"]:
                    status, payload = project_calc_rebuild(project_id)
                elif tail == ["export", "internal"]:
                    status, payload = project_export_internal(project_id)
                elif tail == ["export", "owner"]:
                    status, payload = project_export_owner(project_id)
                else:
                    self._send_json(404, {"error": "not found"})
                    return
                self._send_json(status, payload)
                return
            self._send_json(404, {"error": "not found"})
            return

        if self.path == "/api/v1/intake/upload":
            ctype = self.headers.get("content-type", "")
            if "multipart/form-data" not in ctype:
                self._send_json(400, {"error": "Content-Type must be multipart/form-data"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(length)

                raw_msg = [f"Content-Type: {ctype}".encode('utf-8'), b"", body]
                msg = message_from_bytes(b"\r\n".join(raw_msg))
                
                job_id = _utc_now().replace(":", "").replace("-", "") + "_" + uuid.uuid4().hex[:6]
                tmp_dir = Path(__file__).resolve().parents[2] / "tmp" / f"job_{job_id}"
                tmp_dir.mkdir(parents=True, exist_ok=True)
                
                saved_files = []
                if msg.is_multipart():
                    for part in msg.walk():
                        filename = part.get_filename()
                        if filename:
                            safe_name = Path(filename).name
                            save_path = tmp_dir / safe_name
                            with open(save_path, "wb") as f:
                                payload_bytes = part.get_payload(decode=True)
                                if payload_bytes:
                                    f.write(payload_bytes)
                            saved_files.append(str(save_path.absolute()))
                
                status_code, response = intake_prepare({"files": saved_files})
                if status_code == 200 and response.get("job_id"):
                    uploads = {}
                    for idx, input_item in enumerate(response.get("inputs", [])):
                        stored_path = saved_files[idx]
                        input_item["stored_path"] = stored_path
                        uploads[input_item["file"]] = stored_path
                    self._job_state(str(response["job_id"]))["uploads"] = uploads
                    if saved_files:
                        response["file_path"] = saved_files[0]
                self._send_json(status_code, response)
            except Exception as exc:
                self._send_json(500, {"error": str(exc)})
            return

        if self.path == "/api/v1/takeoff/preview":
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length)
            status_code, payload = preview_from_bytes(body)
            self._send_json(status_code, payload)
            return
        
        handler = self.routes.get(self.path)
        if handler is None:
            self._send_json(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        try:
            payload_data = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            self._send_json(400, {"ok": False, "error": {"code": "invalid_json", "message": str(exc)}})
            return
        payload_data = self._resolve_uploaded_file(payload_data)
        job_id = str(payload_data.get("job_id", ""))
        state = self._job_state(job_id) if job_id else {}
        if self.path == "/api/v1/logic/compute" and not payload_data.get("elements") and state.get("elements"):
            payload_data = dict(payload_data)
            payload_data["elements"] = state["elements"]
        if self.path == "/api/v1/export/xlsx":
            payload_data = dict(payload_data)
            payload_data.setdefault("computed", state.get("computed", []))
            payload_data.setdefault("boq", state.get("boq", {}))
            payload_data.setdefault("workbook_template", state.get("boq", {}).get("template"))
        status_code, payload = handler(payload_data)
        if job_id and status_code == 200 and isinstance(payload, dict):
            if self.path == "/api/v1/map/schema":
                state["elements"] = payload.get("elements", [])
            elif self.path == "/api/v1/extract/dwg":
                state["extract_dwg"] = payload
            elif self.path == "/api/v1/logic/compute":
                state["computed"] = payload.get("computed", [])
            elif self.path == "/api/v1/boq/generate":
                state["boq"] = payload
        self._send_json(status_code, payload)

    def do_PATCH(self) -> None:  # noqa: N802
        parts = self._split_path()
        if parts[:2] != ["api", "v2"] or len(parts) != 4 or parts[2] != "projects":
            self._send_json(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length else b"{}"
        try:
            payload_data = json.loads(body.decode("utf-8")) if body else {}
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            self._send_json(400, {"ok": False, "error": {"code": "invalid_json", "message": str(exc)}})
            return
        status, payload = project_patch(parts[3], payload_data)
        self._send_json(status, payload)

    def log_message(self, format: str, *args: Any) -> None:
        return


def serve(host: str = "127.0.0.1", port: int = 7084) -> None:
    server = ThreadingHTTPServer((host, port), RequestHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
