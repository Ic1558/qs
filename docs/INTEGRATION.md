# Integration

## Candidate Registration

1. Start the module service:

```bash
cd /Users/icmini/0luka/repos/qs
PYTHONPATH=src python3 -m universal_qs_engine.cli serve-health --port 7084
```

2. Add the candidate entry from `ops/module_registry_entry.json` into `0luka/core_brain/ops/module_registry.json`.

3. Validate from the 0luka root:

```bash
python3 core_brain/ops/modulectl.py validate
python3 core_brain/ops/modulectl.py status universal_qs_api
python3 core_brain/ops/modulectl.py health universal_qs_api
```

## Module Boundary

This repo remains a standalone module. The repo boundary is `repos/qs`, while the internal Python package remains `universal_qs_engine`. Hardening for vector extraction, review queues, and export lives inside that package.

0luka core should connect to it only through:

- `manifest.yaml`
- `plugins/0luka_plugin.yaml`
- `ops/module_registry_entry.json`
- the HTTP surface on port `7084`

Core should not duplicate extractor logic; it should treat this repo as an external module lane.

## Expected 0luka Contract

- Launchd label: `com.0luka.universal-qs-api`
- Health URL: `http://127.0.0.1:7084/api/health`
- Preview URL: `http://127.0.0.1:7084/api/v1/takeoff/preview`
- Module API URLs:
  - `/api/v1/intake/prepare`
  - `/api/v1/extract/dwg`
  - `/api/v1/extract/pdf`
  - `/api/v1/map/schema`
  - `/api/v1/logic/compute`
  - `/api/v1/boq/generate`
  - `/api/v1/export/xlsx`
  - `/api/v1/acceptance/evaluate`
- Trace fields: `trace_id`, `job_id`, `source_file`, `discipline`

## Next Implementation Steps

- Replace placeholder extractors with DWG and PDF ingestion adapters.
- Persist normalized JSON takeoff artifacts to `outputs/`.
- Add workbook generation for PO-4, PO-5, and PO-6.
- Add source-link anchors for audit proofs and manual review queue exports.
