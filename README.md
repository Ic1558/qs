# Universal QS Engine

Local-first QS authoring repo that plugs into 0luka later.

This repo is now a `Multi-discipline aggregation engine` supporting Structure, Architecture, and MEP.

## Current Milestone

- `ST Gate`: CLEARED
- `AR Gate`: OPEN (PROVEN via multi-discipline aggregation)
- `MEP Gate`: OPEN (PROVEN via multi-discipline aggregation)
- `Universal Gate`: CLEARED (PROVEN via Bridge & Orchestration)

What this means:
- multi-discipline aggregation engine is live (ST/AR/MEP)
- AR wall deductions and finish mapping are functional
- MEP count/run items are supported and traceable
- module is fully integrated into 0luka bridge/CLEC pipeline
- automated task orchestration via `qs.generate_boq` intent is active
- workbook traceability covers deduction rules and discipline tags

## Scope Right Now

The repo currently owns:
- project state
- multi-discipline aggregation engine
- AR/MEP specialized member models
- 0luka bridge adapter and task orchestration logic
- source registry
- rate library
- takeoff workspace
- calc graph
- review engine
- web API and local UI
- adapter to `tools/qs_engine`


The repo does not yet claim:
- accepted AR quantity workflow
- accepted MEP quantity workflow
- universal automatic takeoff
- production-grade drawing extraction for all disciplines

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
NO_START=1 zsh tools/bootstrap.zsh
python3 -m unittest discover -s tests
PYTHONPATH=src python3 -m universal_qs_engine.cli health
PYTHONPATH=src python3 -m universal_qs_engine.cli preview --input examples/request.json
PYTHONPATH=src python3 -m universal_qs_engine.cli api intake_prepare --input examples/intake_prepare.json
PYTHONPATH=src python3 -m universal_qs_engine.cli api optimize_plan --input examples/request.json
PYTHONPATH=src python3 -m universal_qs_engine.cli serve-health --port 7084
```

## Acceptance Discipline

Do not claim a discipline gate from fixtures or unit tests alone.

A gate is cleared only when:
- a real project runs through `repos/qs` project state
- review/export behavior is exercised from the app/domain layer
- the output workbook traces correctly to the underlying member and source basis

Current accepted proof:
- `ST Gate` cleared from Kamolpat structure workflow

See [ACCEPTANCE.md](/Users/icmini/0luka/repos/qs/docs/ACCEPTANCE.md).
See [AR_MEMBER_MODEL.md](/Users/icmini/0luka/repos/qs/docs/AR_MEMBER_MODEL.md) before any AR feature work starts.

## 0luka Integration

- Repo boundary: `repos/qs`
- Internal Python package: `src/universal_qs_engine`
- Module contract: `manifest.yaml`
- Plugin governance contract: `plugins/0luka_plugin.yaml`
- Candidate registry payload: `ops/module_registry_entry.json`
- Launchd template: `ops/com.0luka.universal-qs-api.plist.template`

See `docs/INTEGRATION.md` for the registration steps.

See `docs/API_CONTRACTS.md`, `docs/ACCEPTANCE.md`, and `docs/RUNBOOK.md` for the expanded spec alignment and operator guidance.
