from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from universal_qs_engine.boq_extractor_v2 import extract_boq_v2
from universal_qs_engine.errors import QSJobError
from universal_qs_engine.job_registry import run_registered_job
from tests.dxf_fixture import write_minimal_dxf


class BOQExtractorV2Tests(unittest.TestCase):
    def test_extracts_normalized_quantities_from_dxf_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            fixture = write_minimal_dxf(Path(tmpdir) / "minimal_vector.dxf")
            payload = extract_boq_v2(source_ref=str(fixture))
            self.assertEqual(payload["source_kind"], "dxf")
            self.assertEqual(payload["quantity_schema_version"], "qs.boq_extract.v2")
            self.assertEqual(payload["metrics"]["kept_entities"], 2)
            self.assertEqual(len(payload["normalized_quantities"]), 2)
            slab = next(item for item in payload["normalized_quantities"] if item["category"] == "slab")
            self.assertEqual(slab["measurements"]["area_m2"], 100.0)

    @patch("universal_qs_engine.extractor_pdf.pdfplumber.open")
    def test_extracts_normalized_quantities_from_pdf_fixture(self, mock_pdf_open: MagicMock) -> None:
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.lines = [{"width": 3, "height": 4}]
        mock_page.rects = [{"width": 10, "height": 20}]
        mock_page.curves = []
        mock_pdf.pages = [mock_page]
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf

        payload = extract_boq_v2(source_ref="/tmp/mock_vector.pdf")
        self.assertEqual(payload["source_kind"], "pdf")
        self.assertEqual(len(payload["normalized_quantities"]), 2)
        rect = next(item for item in payload["normalized_quantities"] if item["measurements"].get("area_m2"))
        self.assertEqual(rect["measurements"]["area_m2"], 200.0)

    def test_rejects_unsupported_source_suffix(self) -> None:
        with self.assertRaises(QSJobError):
            extract_boq_v2(source_ref="/tmp/input.xlsx")

    def test_boq_job_embeds_normalized_details_when_explicit_inputs_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            fixture = write_minimal_dxf(Path(tmpdir) / "minimal_vector.dxf")
            result = run_registered_job(
                "qs.boq_extract",
                {
                    "run_id": "run_boq_v2_001",
                    "project_id": "prj_boq_v2_001",
                    "inputs": {
                        "source_ref": str(fixture),
                        "measurement_system": "metric",
                    },
                },
            )
            self.assertEqual(result["job_type"], "qs.boq_extract")
            self.assertEqual(
                result["details"]["boq_extract"]["quantity_schema_version"],
                "qs.boq_extract.v2",
            )


if __name__ == "__main__":
    unittest.main()
