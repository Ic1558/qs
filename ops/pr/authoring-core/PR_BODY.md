## Metadata

- trace_id: qs-authoring-core-a9b1
- intent: authoring-core
- executor: Codex IDE ([Lisa])
- level: L3

## What Changed

- add project/takeoff authoring core modules for storage, calc graph, review, acceptance, aggregation, drawing import, and internal workbook export
- extend `src/universal_qs_engine/api.py` with project authoring functions used by the new tests and proof script
- harden `src/universal_qs_engine/qs_engine_adapter.py` so `qs_engine` loads lazily at export time instead of breaking import-time test collection

## Artifacts

- `ops/pr/authoring-core/PLAN.md`
- `ops/pr/authoring-core/DIFF.md`
- `ops/pr/authoring-core/VERIFY.md`

## Verify

- `PYTHONPATH=src:/Users/icmini/0luka/tools python3 -m pytest -q tests/test_authoring_flow.py tests/test_discipline_aggregation.py`
- `python3 verify_phase6_proof.py`
