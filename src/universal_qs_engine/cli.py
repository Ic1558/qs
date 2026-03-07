from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

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
)
from .service import build_health_payload, preview_from_payload, serve


def _print_json(payload: Any) -> None:
    print(json.dumps(payload, indent=2))


def _cmd_health(_: argparse.Namespace) -> int:
    _print_json(build_health_payload())
    return 0


def _cmd_preview(args: argparse.Namespace) -> int:
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    _print_json(preview_from_payload(payload))
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    serve(host=args.host, port=args.port)
    return 0


def _cmd_api(args: argparse.Namespace) -> int:
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    handlers = {
        "intake_prepare": intake_prepare,
        "extract_dwg": extract_dwg,
        "extract_pdf": extract_pdf,
        "map_schema": map_schema,
        "logic_compute": logic_compute,
        "boq_generate": boq_generate,
        "export_xlsx": export_xlsx,
        "acceptance_evaluate": acceptance_evaluate,
        "optimize_plan": optimize_plan,
    }
    status_code, response = handlers[args.endpoint](payload)
    _print_json({"status_code": status_code, "response": response})
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="uqs", description="Universal QS Engine helper CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    health = subparsers.add_parser("health", help="Print service health payload")
    health.set_defaults(func=_cmd_health)

    preview = subparsers.add_parser("preview", help="Preview a takeoff request from JSON")
    preview.add_argument("--input", required=True, help="Path to a JSON request payload")
    preview.set_defaults(func=_cmd_preview)

    serve_cmd = subparsers.add_parser("serve-health", help="Serve module health and preview endpoints")
    serve_cmd.add_argument("--host", default="127.0.0.1")
    serve_cmd.add_argument("--port", type=int, default=7084)
    serve_cmd.set_defaults(func=_cmd_serve)

    api_cmd = subparsers.add_parser("api", help="Run a module API handler against JSON input")
    api_cmd.add_argument(
        "endpoint",
        choices=[
            "intake_prepare",
            "extract_dwg",
            "extract_pdf",
            "map_schema",
            "logic_compute",
            "boq_generate",
            "export_xlsx",
            "acceptance_evaluate",
            "optimize_plan",
        ],
    )
    api_cmd.add_argument("--input", required=True, help="Path to a JSON payload")
    api_cmd.set_defaults(func=_cmd_api)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
