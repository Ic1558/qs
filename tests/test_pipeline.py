from __future__ import annotations

import json
import unittest
from pathlib import Path

from universal_qs_engine.contracts import TakeoffRequest
from universal_qs_engine.pipeline import WORKBOOK_TABS, build_preview_result


ROOT = Path(__file__).resolve().parents[1]


class PipelineTests(unittest.TestCase):
    def _load_request(self) -> TakeoffRequest:
        payload = json.loads((ROOT / "examples" / "request.json").read_text(encoding="utf-8"))
        return TakeoffRequest.from_dict(payload)

    def test_preview_flags_missing_pdf_scale(self) -> None:
        result = build_preview_result(self._load_request())
        codes = {item.code for item in result.review_queue}
        self.assertIn("pdf_scale_required", codes)
        self.assertEqual(result.status, "review_required")

    def test_preview_includes_po_workbook_tabs(self) -> None:
        result = build_preview_result(self._load_request())
        self.assertEqual(result.workbook.tabs, WORKBOOK_TABS)
        self.assertEqual(result.integration["module_label"], "com.0luka.universal-qs-api")

    def test_preview_builds_three_disciplines(self) -> None:
        result = build_preview_result(self._load_request())
        disciplines = {item.discipline for item in result.elements}
        self.assertEqual(disciplines, {"architecture", "structure", "mep"})


if __name__ == "__main__":
    unittest.main()
