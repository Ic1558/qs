from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from universal_qs_engine.api import acceptance_evaluate, extract_dwg, extract_pdf, export_xlsx, intake_prepare, optimize_plan
from universal_qs_engine.service import build_health_payload, preview_from_bytes
from universal_qs_engine.workbook import build_workbook_template
from tests.dxf_fixture import write_minimal_dxf


ROOT = Path(__file__).resolve().parents[1]


class ServiceTests(unittest.TestCase):
    def test_health_payload_is_ok(self) -> None:
        payload = build_health_payload()
        self.assertEqual(payload["status"], "ok")
        self.assertIn("/api/health", payload["endpoints"])
        self.assertIn("/api/v1/intake/upload", payload["endpoints"])

    def test_preview_endpoint_accepts_example_payload(self) -> None:
        raw = (ROOT / "examples" / "request.json").read_bytes()
        status_code, payload = preview_from_bytes(raw)
        self.assertEqual(status_code, 200)
        self.assertEqual(payload["job_id"], "qs-demo-001")
        self.assertEqual(payload["schema_version"], "universal_qs_result_v1")

    def test_preview_endpoint_rejects_invalid_json(self) -> None:
        status_code, payload = preview_from_bytes(b"{bad json")
        self.assertEqual(status_code, 400)
        self.assertIn("error", payload)

    def test_intake_prepare_returns_job_id_and_inputs(self) -> None:
        payload = json.loads((ROOT / "examples" / "intake_prepare.json").read_text(encoding="utf-8"))
        status_code, response = intake_prepare(payload)
        self.assertEqual(status_code, 200)
        self.assertTrue(response["job_id"].startswith("job_"))
        self.assertEqual(len(response["inputs"]), 2)

    def test_extract_pdf_blocks_without_scale(self) -> None:
        payload = json.loads((ROOT / "examples" / "extract_pdf_missing_scale.json").read_text(encoding="utf-8"))
        status_code, response = extract_pdf(payload)
        self.assertEqual(status_code, 422)
        self.assertEqual(response["error"]["code"], "missing_scale")

    def test_extract_dwg_uses_real_fixture_and_returns_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            fixture = write_minimal_dxf(Path(tmpdir) / "minimal_vector.dxf")
            status_code, response = extract_dwg({"file": str(fixture)})
            self.assertEqual(status_code, 200)
            self.assertEqual(response["mode"], "vector_ezdxf")
            self.assertEqual(response["entity_count"], 2)
            self.assertEqual(response["metrics"]["skipped_annotations"], 1)
            self.assertEqual(response["mapped_count"], 2)
            self.assertEqual(response["generic_count"], 0)

    def test_extract_dwg_missing_file_fails_closed(self) -> None:
        status_code, response = extract_dwg({"file": str(ROOT / "tests" / "fixtures" / "missing.dxf")})
        self.assertEqual(status_code, 404)
        self.assertEqual(response["error"]["code"], "source_file_missing")

    def test_export_blocks_on_conflicts(self) -> None:
        status_code, response = export_xlsx({"job_id": "job_x", "conflicts_acknowledged": False})
        self.assertEqual(status_code, 409)
        self.assertEqual(response["error"]["code"], "conflicting_quantities")

    def test_export_writes_real_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            status_code, response = export_xlsx(
                {
                    "job_id": "job_real",
                    "conflicts_acknowledged": True,
                    "computed": [{"id": "CMP-001", "category": "wall_finish", "qty": 12, "unit": "m2", "source_id": "A1"}],
                    "boq": {"direct_cost": 12000, "factor_f": 1.1, "vat_enabled": True},
                    "output_dir": tmpdir,
                }
            )
            self.assertEqual(status_code, 200)
            xlsx_path = Path(response["xlsx"])
            json_path = Path(response["json"])
            self.assertTrue(xlsx_path.exists())
            self.assertTrue(json_path.exists())
            with ZipFile(xlsx_path) as workbook:
                self.assertIn("xl/workbook.xml", workbook.namelist())

    def test_workbook_template_contains_named_ranges(self) -> None:
        template = build_workbook_template()
        self.assertIn("DIRECT_COST", template["named_ranges"])
        self.assertIn("PO-4", template["sheets"])

    def test_acceptance_gate_passes_expected_metrics(self) -> None:
        payload = json.loads((ROOT / "examples" / "acceptance_pass.json").read_text(encoding="utf-8"))
        status_code, response = acceptance_evaluate(payload)
        self.assertEqual(status_code, 200)
        self.assertTrue(response["ok"])

    def test_optimize_plan_returns_smart_low_cost_mode(self) -> None:
        payload = json.loads((ROOT / "examples" / "request.json").read_text(encoding="utf-8"))
        status_code, response = optimize_plan(payload)
        self.assertEqual(status_code, 200)
        self.assertEqual(response["optimization"]["mode"], "smart_low_cost")


if __name__ == "__main__":
    unittest.main()
