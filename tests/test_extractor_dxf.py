from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from universal_qs_engine.extractor_dxf import extract_dxf_entities
from tests.dxf_fixture import write_minimal_dxf


ROOT = Path(__file__).resolve().parents[1]


class ExtractorDXFTests(unittest.TestCase):
    def test_extracts_real_vector_geometry_from_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            fixture = write_minimal_dxf(Path(tmpdir) / "minimal_vector.dxf")
            payload = extract_dxf_entities(str(fixture))
            metrics = payload["metrics"]
            entities = payload["entities"]

            self.assertEqual(metrics["extractor"], "ezdxf")
            self.assertEqual(metrics["total_entities"], 3)
            self.assertEqual(metrics["skipped_annotations"], 1)
            self.assertEqual(metrics["kept_entities"], 2)
            self.assertEqual(len(entities), 2)

            line = next(entity for entity in entities if entity["type"] == "line")
            slab = next(entity for entity in entities if entity["type"] == "lwpolyline")

            self.assertEqual(line["length_m"], 5.0)
            self.assertEqual(slab["length_m"], 40.0)
            self.assertEqual(slab["area_m2"], 100.0)
            self.assertEqual(metrics["geometry_measured_entities"], 2)


if __name__ == "__main__":
    unittest.main()
