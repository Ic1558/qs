# API Contracts

The module exposes the following JSON endpoints:

- `/api/v1/intake/prepare`
- `/api/v1/extract/dwg`
- `/api/v1/extract/pdf`
- `/api/v1/map/schema`
- `/api/v1/logic/compute`
- `/api/v1/boq/generate`
- `/api/v1/export/xlsx`
- `/api/v1/acceptance/evaluate`
- `/api/v1/optimize/plan`
- `/api/v1/takeoff/preview`

## Notes

- `extract/pdf` blocks with `422 missing_scale` if no calibration is supplied.
- `extract/pdf` emits a `low_symbol_confidence` warning for symbols below `0.95`.
- `extract/dwg` can assign unmapped layers to `Unclassified`.
- `export/xlsx` blocks on unresolved cross-discipline conflicts unless acknowledged.
- `acceptance/evaluate` encodes the final release gate from the spec.
- `optimize/plan` returns a cheap-first execution strategy for lower-cost runs.
