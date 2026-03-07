# Cost Optimization

The repo now exposes a cheap-first planning layer through `/api/v1/optimize/plan`.

## Default strategy

- Prefer `DWG/DXF` over PDF when both sources exist.
- Skip OCR for vector PDFs and use native geometry/text extraction.
- Restrict OCR and symbol detection to target pages for scanned PDFs.
- Reuse project defaults for heights and waste before expensive inference.
- Export JSON first when review is pending; defer full XLSX generation.
- Generate pricing and executive summary after PO-4 quantities stabilize.
- Enforce cache-first reruns and delta execution for pricing-only updates.
- Keep heavy vision disabled by default; require explicit approval.

## Why this lowers cost

- OCR and symbol detection are the expensive part of PDF intake.
- Workbook export is delayed until blockers are cleared.
- Manual review scope is narrowed to low-confidence detections only.
- Cache hits prevent full reprocessing of the same pages.

## Guardrails (Low-Cost Mode)

- OCR page cap: 15% of total pages.
- Vision page cap: 5% of total pages.
- Storage cap: 200 MB per project (cache included).
- Runtime cap: 8 minutes per standard plan.
- Parity gate: PDF vs DWG parity < 2%.

## Execution Controls

- Vision is disabled by default.
- Vision requires explicit approval when cheaper paths fail.
- Manual riser inputs are used for minimal MEP support.
- Delta execution skips re-extraction when only pricing/Factor F changes.

## Low-Cost Stack (Open Source)

- CAD: `ezdxf`
- PDF vector: `pdfplumber` or `pypdf`
- OCR: `tesseract` (local)
- Vision: small ONNX model (optional)
- Spreadsheet: `openpyxl` or `xlsxwriter`
- Local storage: SQLite (optional)
