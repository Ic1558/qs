from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = ROOT / "outputs"


def output_url(path_str: str) -> str:
    path = Path(path_str)
    try:
        rel = path.relative_to(DEFAULT_OUTPUT_DIR)
    except ValueError:
        return path.as_posix()
    return f"/outputs/{rel.as_posix()}"


def _col_name(index: int) -> str:
    result = ""
    while index > 0:
        index, rem = divmod(index - 1, 26)
        result = chr(65 + rem) + result
    return result


def _cell_xml(ref: str, value) -> str:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f'<c r="{ref}"><v>{value}</v></c>'
    text = escape("" if value is None else str(value))
    return f'<c r="{ref}" t="inlineStr"><is><t>{text}</t></is></c>'


def _worksheet_xml(rows: list[list[object]]) -> str:
    row_xml = []
    for row_idx, row in enumerate(rows, start=1):
        cells = []
        for col_idx, value in enumerate(row, start=1):
            ref = f"{_col_name(col_idx)}{row_idx}"
            cells.append(_cell_xml(ref, value))
        row_xml.append(f'<row r="{row_idx}">{"".join(cells)}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(row_xml)}</sheetData>'
        "</worksheet>"
    )


def _content_types(sheet_count: int) -> str:
    overrides = [
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>',
        '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>',
        '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>',
    ]
    for idx in range(1, sheet_count + 1):
        overrides.append(
            f'<Override PartName="/xl/worksheets/sheet{idx}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        f'{"".join(overrides)}'
        "</Types>"
    )


def _root_rels() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
        '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
        "</Relationships>"
    )


def _workbook_xml(sheet_names: list[str]) -> str:
    sheets = []
    for idx, name in enumerate(sheet_names, start=1):
        sheets.append(f'<sheet name="{escape(name)}" sheetId="{idx}" r:id="rId{idx}"/>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheets>{"".join(sheets)}</sheets>'
        "</workbook>"
    )


def _workbook_rels(sheet_count: int) -> str:
    rels = []
    for idx in range(1, sheet_count + 1):
        rels.append(
            f'<Relationship Id="rId{idx}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{idx}.xml"/>'
        )
    rels.append(
        f'<Relationship Id="rId{sheet_count + 1}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/>'
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'{"".join(rels)}'
        "</Relationships>"
    )


def _styles_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>'
        '<fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
        '<borders count="1"><border/></borders>'
        '<cellStyleXfs count="1"><xf/></cellStyleXfs>'
        '<cellXfs count="1"><xf xfId="0"/></cellXfs>'
        '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
        "</styleSheet>"
    )


def _core_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        "<dc:title>Universal QS Engine Export</dc:title>"
        "<dc:creator>universal_qs_engine</dc:creator>"
        "</cp:coreProperties>"
    )


def _app_xml(sheet_count: int) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
        'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
        "<Application>universal_qs_engine</Application>"
        f"<Sheets>{sheet_count}</Sheets>"
        "</Properties>"
    )


def _build_sheet_rows(job_id: str, computed: list[dict], boq: dict, workbook_template: dict) -> dict[str, list[list[object]]]:
    po4 = [workbook_template["sheets"]["PO-4"]["columns"]]
    for idx, item in enumerate(computed, start=1):
        po4.append(
            [
                idx,
                item.get("discipline", "unknown"),
                item.get("category", "generic"),
                item.get("source_id", item.get("id", "")),
                item.get("qty", 0),
                item.get("unit", ""),
                item.get("formula", ""),
                item.get("source_file", ""),
                item.get("notes", ""),
            ]
        )

    grouped: dict[str, list[dict]] = defaultdict(list)
    for item in computed:
        grouped[item.get("category", "generic")].append(item)

    po5 = [workbook_template["sheets"]["PO-5"]["columns"]]
    for category, items in grouped.items():
        qty = sum(float(item.get("qty", 0)) for item in items)
        material_rate = 1000.0
        labor_rate = 500.0
        material_total = round(qty * material_rate, 2)
        labor_total = round(qty * labor_rate, 2)
        po5.append([category, qty, items[0].get("unit", ""), material_rate, labor_rate, material_total, labor_total, material_total + labor_total])

    direct_cost = float(boq.get("direct_cost", 0.0))
    factor_f = float(boq.get("factor_f", 1.0))
    vat_enabled = bool(boq.get("vat_enabled", True))
    vat_multiplier = 1.07 if vat_enabled else 1.0
    final_bid = round(direct_cost * factor_f * vat_multiplier, 2)
    po6 = [[field, ""] for field in workbook_template["sheets"]["PO-6"]["fields"]]
    po6[0][1] = direct_cost
    po6[1][1] = factor_f
    po6[2][1] = "ON" if vat_enabled else "OFF"
    po6[3][1] = final_bid

    proofs = [["Element ID", "Formula", "Proof JSON", "Source Link"]]
    for item in computed:
        proofs.append([item.get("id", ""), item.get("formula", ""), json.dumps(item.get("proof", {}), ensure_ascii=False), item.get("source_file", "")])

    review = [["Severity", "Code", "Message", "Source File", "Resolution Status"]]
    review.append(["info", "pilot", f"Export generated for {job_id}", "", "complete"])

    factor_f_table = [workbook_template["sheets"]["FactorF_Table"]["columns"], [0, 100000000, 1.272, 1.180]]

    return {
        "PO-4": po4,
        "PO-5": po5,
        "PO-6": po6,
        "Proofs": proofs,
        "Manual Review": review,
        "FactorF_Table": factor_f_table,
    }


def write_export_bundle(job_id: str, computed: list[dict], boq: dict, workbook_template: dict, output_dir: str | Path | None = None) -> tuple[str, str]:
    output_root = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    output_root.mkdir(parents=True, exist_ok=True)

    xlsx_path = output_root / f"{job_id}_PO_4_5_6.xlsx"
    json_path = output_root / f"{job_id}_takeoff.json"

    sheets = _build_sheet_rows(job_id, computed, boq, workbook_template)
    sheet_names = list(sheets.keys())

    with ZipFile(xlsx_path, "w", compression=ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _content_types(len(sheet_names)))
        zf.writestr("_rels/.rels", _root_rels())
        zf.writestr("docProps/core.xml", _core_xml())
        zf.writestr("docProps/app.xml", _app_xml(len(sheet_names)))
        zf.writestr("xl/workbook.xml", _workbook_xml(sheet_names))
        zf.writestr("xl/_rels/workbook.xml.rels", _workbook_rels(len(sheet_names)))
        zf.writestr("xl/styles.xml", _styles_xml())
        for idx, name in enumerate(sheet_names, start=1):
            zf.writestr(f"xl/worksheets/sheet{idx}.xml", _worksheet_xml(sheets[name]))

    json_payload = {
        "job_id": job_id,
        "computed": computed,
        "boq": boq,
        "workbook_template": workbook_template,
    }
    json_path.write_text(json.dumps(json_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return str(xlsx_path), str(json_path)
