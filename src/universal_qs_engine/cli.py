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
    project_aggregate,
    project_acceptance_override,
    project_export_internal,
    project_review_ack,
    project_review_override,
    project_acceptance_get,
)
from .service import build_health_payload, preview_from_payload, serve


def _print_json(payload: Any) -> None:
    print(json.dumps(payload, indent=2))


def _emit_response(status_code: int, response: Any) -> int:
    _print_json({"status_code": status_code, "response": response})
    return 0 if status_code < 400 else 1


def _cmd_health(_: argparse.Namespace) -> int:
    _print_json(build_health_payload())
    return 0


def _cmd_generate_boq(args: argparse.Namespace) -> int:
    project_id = args.project_id
    
    # 1. Aggregate + Recalc
    status, agg_resp = project_aggregate(project_id)
    if status != 200:
        _print_json({"status": "error", "step": "aggregate", "response": agg_resp})
        return 1
        
    # 2. Acceptance Check
    status, acc_resp = project_acceptance_get(project_id)
    if status != 200:
        _print_json({"status": "error", "step": "acceptance", "response": acc_resp})
        return 1
        
    evaluation = acc_resp.get("evaluation", {})
    
    # 3. Export (Internal always, Owner only if accepted)
    # We always export internal trace for audit.
    status, exp_int_resp = project_export_internal(project_id)
    if status != 200:
        _print_json({"status": "error", "step": "export_internal", "response": exp_int_resp})
        return 1
        
    # Attempt owner export (gated)
    from .api import project_export_owner
    status, exp_own_resp = project_export_owner(project_id)
    
    owner_ok = (status == 200)
    
    result = {
        "status": "success" if owner_ok else "blocked",
        "project_id": project_id,
        "acceptance": evaluation,
        "artifacts": {
            "internal_trace_xlsx": exp_int_resp.get("xlsx"),
            "owner_workbook_xlsx": exp_own_resp.get("xlsx") if owner_ok else None,
        }
    }
    if not owner_ok:
        result["block_reason"] = exp_own_resp.get("error", {}).get("message")
        result["fallbacks"] = exp_own_resp.get("fallbacks", [])

    _print_json(result)
    return 0 if owner_ok else 2 # Exit code 2 for blocked/fail-closed


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
    return _emit_response(status_code, response)


def _cmd_project_acceptance(args: argparse.Namespace) -> int:
    status_code, response = project_acceptance_get(args.project_id)
    return _emit_response(status_code, response)


def _cmd_project_acceptance_override(args: argparse.Namespace) -> int:
    status_code, response = project_acceptance_override(
        args.project_id,
        {
            "justification": args.justification,
            "author": args.author,
        },
    )
    return _emit_response(status_code, response)


def _cmd_project_review_ack(args: argparse.Namespace) -> int:
    status_code, response = project_review_ack(
        args.project_id,
        {
            "flag_id": args.flag_id,
            "comment": args.comment,
        },
    )
    return _emit_response(status_code, response)


def _cmd_project_review_override(args: argparse.Namespace) -> int:
    status_code, response = project_review_override(
        args.project_id,
        {
            "segment_id": args.segment_id,
            "field": args.field,
            "value": args.value,
            "justification": args.justification,
            "flag_id": args.flag_id,
        },
    )
    return _emit_response(status_code, response)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="uqs", description="Universal QS Engine helper CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    health = subparsers.add_parser("health", help="Print service health payload")
    health.set_defaults(func=_cmd_health)

    gen_boq = subparsers.add_parser("generate-boq", help="Run full pipeline: aggregate + acceptance + export")
    gen_boq.add_argument("--project-id", required=True, help="ID of the project to process")
    gen_boq.set_defaults(func=_cmd_generate_boq)

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

    acceptance_get_cmd = subparsers.add_parser("project-acceptance", help="Show acceptance evaluation for a project")
    acceptance_get_cmd.add_argument("--project-id", required=True, help="ID of the project to inspect")
    acceptance_get_cmd.set_defaults(func=_cmd_project_acceptance)

    acceptance_override_cmd = subparsers.add_parser("project-acceptance-override", help="Apply an acceptance override")
    acceptance_override_cmd.add_argument("--project-id", required=True, help="ID of the project to override")
    acceptance_override_cmd.add_argument("--justification", required=True, help="Why the acceptance override is allowed")
    acceptance_override_cmd.add_argument("--author", default="human_reviewer", help="Author recorded in the override audit trail")
    acceptance_override_cmd.set_defaults(func=_cmd_project_acceptance_override)

    review_ack_cmd = subparsers.add_parser("project-review-ack", help="Attach an acknowledgement note to a review flag")
    review_ack_cmd.add_argument("--project-id", required=True, help="ID of the project")
    review_ack_cmd.add_argument("--flag-id", required=True, help="Review flag identifier")
    review_ack_cmd.add_argument("--comment", required=True, help="Operator note for the review flag")
    review_ack_cmd.set_defaults(func=_cmd_project_review_ack)

    review_override_cmd = subparsers.add_parser("project-review-override", help="Apply a deterministic segment override")
    review_override_cmd.add_argument("--project-id", required=True, help="ID of the project")
    review_override_cmd.add_argument("--segment-id", required=True, help="Segment identifier")
    review_override_cmd.add_argument("--field", required=True, choices=["length", "width", "depth"], help="Segment field to override")
    review_override_cmd.add_argument("--value", required=True, type=float, help="Replacement numeric value")
    review_override_cmd.add_argument("--justification", required=True, help="Why the override is valid")
    review_override_cmd.add_argument("--flag-id", default=None, help="Optional review flag to resolve together with the override")
    review_override_cmd.set_defaults(func=_cmd_project_review_override)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
