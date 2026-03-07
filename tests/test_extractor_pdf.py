from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from universal_qs_engine.extractor_pdf import extract_pdf_entities

class ExtractorPDFTests(unittest.TestCase):
    @patch("universal_qs_engine.extractor_pdf.pdfplumber.open")
    def test_extracts_pdf_vector_geometry(self, mock_pdf_open) -> None:
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.lines = [
            {"width": 30, "height": 40}, # length=50
            {"width": 0, "height": 10},  # length=10
            {"width": 0, "height": 0.5}, # Too small, ignored
        ]
        mock_page.rects = [
            {"width": 10, "height": 20}, # area=200, length=60
            {"width": 0.1, "height": 0.1}, # Too small, ignored
        ]
        mock_page.curves = [{"some": "curve"}]
        
        mock_pdf.pages = [mock_page]
        
        # enter mock ctx manager
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf
        
        # scale 0.1 means length 50 -> 5.0, area 200 -> 2.0
        payload = extract_pdf_entities("/mock/path.pdf", scale_factor=0.1)
        
        metrics = payload["metrics"]
        entities = payload["entities"]
        
        self.assertEqual(metrics["extractor"], "pdfplumber")
        self.assertEqual(metrics["vector_pages"], 0)
        self.assertEqual(metrics["raster_pages"], 1) # < 50 vectors
        self.assertEqual(metrics["kept_entities"], 3) # 2 lines, 1 rect
        self.assertEqual(metrics["generic_entities"], 3)
        self.assertEqual(metrics["review_required_entities"], 1) # Top 10 rects added to review
        
        self.assertEqual(len(entities), 3)
        
        lines = [e for e in entities if e["type"] == "line"]
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0]["length_m"], 5.0)
        self.assertEqual(lines[1]["length_m"], 1.0)
        
        rects = [e for e in entities if e["type"] == "rect"]
        self.assertEqual(len(rects), 1)
        self.assertEqual(rects[0]["area_m2"], 2.0)
        self.assertEqual(rects[0]["length_m"], 6.0)

if __name__ == "__main__":
    unittest.main()
