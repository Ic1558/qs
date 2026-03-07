# Universal QS Engine

Standalone repo scaffold for a Universal Quantity Surveying engine that can plug into 0luka core.

This repo is intended to stay as a separate module repo. 0luka core integrates with it through the declared module manifest, plugin contract, and health/API endpoints rather than by inlining the extraction logic into core.

## Scope

This repo packages the concept from `chats_2026-03-06_spec_plan_dod_pprs.md` into a 0luka-compatible module:

- Intake for PDF and DWG/DXF sources
- Normalized cross-discipline takeoff schema
- Architecture, Structure, and MEP logic placeholders
- BOQ workbook planning for PO-4, PO-5, and PO-6
- Auditability and manual-review queue hooks
- Standard-library health/API surface for 0luka module registration
- Module-level API contracts for intake, extraction, schema mapping, logic, BOQ generation, export, and acceptance gating
- Smart low-cost optimization planning that prefers cheaper extraction paths before full processing

## Layout

```text
qs/
├── manifest.yaml
├── plugins/0luka_plugin.yaml
├── ops/module_registry_entry.json
├── src/universal_qs_engine/
├── tests/
├── docs/
└── examples/
```

## Quick Start

```bash
cd /Users/icmini/0luka/repos/qs
python3 -m unittest discover -s tests
PYTHONPATH=src python3 -m universal_qs_engine.cli health
PYTHONPATH=src python3 -m universal_qs_engine.cli preview --input examples/request.json
PYTHONPATH=src python3 -m universal_qs_engine.cli api intake_prepare --input examples/intake_prepare.json
PYTHONPATH=src python3 -m universal_qs_engine.cli api optimize_plan --input examples/request.json
PYTHONPATH=src python3 -m universal_qs_engine.cli serve-health --port 7084
```

## 0luka Integration

- Repo boundary: `repos/qs`
- Internal Python package: `src/universal_qs_engine`
- Module contract: `manifest.yaml`
- Plugin governance contract: `plugins/0luka_plugin.yaml`
- Candidate registry payload: `ops/module_registry_entry.json`
- Launchd template: `ops/com.0luka.universal-qs-api.plist.template`

See `docs/INTEGRATION.md` for the registration steps.

See `docs/API_CONTRACTS.md` and `docs/ACCEPTANCE.md` for the expanded spec alignment.
