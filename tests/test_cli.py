from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from universal_qs_engine import cli


class CliTests(unittest.TestCase):
    def test_project_acceptance_command_returns_zero_on_success(self) -> None:
        args = cli.build_parser().parse_args(["project-acceptance", "--project-id", "prj_123"])
        with patch("universal_qs_engine.cli.project_acceptance_get", return_value=(200, {"ok": True, "evaluation": {"ok": True}})):
            with redirect_stdout(io.StringIO()) as buf:
                rc = args.func(args)
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["status_code"], 200)
        self.assertTrue(payload["response"]["ok"])

    def test_project_acceptance_override_command_passes_author_and_justification(self) -> None:
        args = cli.build_parser().parse_args(
            [
                "project-acceptance-override",
                "--project-id",
                "prj_123",
                "--justification",
                "Approved for owner export",
                "--author",
                "IC",
            ]
        )
        with patch("universal_qs_engine.cli.project_acceptance_override", return_value=(200, {"ok": True})) as mocked:
            with redirect_stdout(io.StringIO()):
                rc = args.func(args)
        self.assertEqual(rc, 0)
        mocked.assert_called_once_with(
            "prj_123",
            {
                "justification": "Approved for owner export",
                "author": "IC",
            },
        )

    def test_project_review_ack_command_returns_error_code_on_failure(self) -> None:
        args = cli.build_parser().parse_args(
            [
                "project-review-ack",
                "--project-id",
                "prj_123",
                "--flag-id",
                "flag_1",
                "--comment",
                "Reviewed with note",
            ]
        )
        with patch("universal_qs_engine.cli.project_review_ack", return_value=(404, {"error": {"code": "project_not_found"}})):
            with redirect_stdout(io.StringIO()) as buf:
                rc = args.func(args)
        self.assertEqual(rc, 1)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["status_code"], 404)

    def test_project_review_override_command_maps_optional_flag(self) -> None:
        args = cli.build_parser().parse_args(
            [
                "project-review-override",
                "--project-id",
                "prj_123",
                "--segment-id",
                "seg_9",
                "--field",
                "depth",
                "--value",
                "0.45",
                "--justification",
                "Measured on section detail",
                "--flag-id",
                "flag_9",
            ]
        )
        with patch("universal_qs_engine.cli.project_review_override", return_value=(200, {"ok": True})) as mocked:
            with redirect_stdout(io.StringIO()):
                rc = args.func(args)
        self.assertEqual(rc, 0)
        mocked.assert_called_once_with(
            "prj_123",
            {
                "segment_id": "seg_9",
                "field": "depth",
                "value": 0.45,
                "justification": "Measured on section detail",
                "flag_id": "flag_9",
            },
        )


if __name__ == "__main__":
    unittest.main()
