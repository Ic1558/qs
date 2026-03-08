## Metadata

- trace_id: qs-authoring-api-ui-b732
- intent: authoring-api-ui
- executor: Codex IDE ([Lisa])
- level: L3

## What Changed

- wire the authoring-core project functions into `src/universal_qs_engine/service.py`
- replace the previous UI with the authoring workspace in `src/universal_qs_engine/ui/`
- add service-layer regression coverage for v2 routes and static UI delivery

## Stacking

- base branch: `codex/feat-authoring-core-a9b1`
- depends on: [Ic1558/qs#2](https://github.com/Ic1558/qs/pull/2)

## Artifacts

- `ops/pr/authoring-api-ui/PLAN.md`
- `ops/pr/authoring-api-ui/DIFF.md`
- `ops/pr/authoring-api-ui/VERIFY.md`

## Verify

- `PYTHONPATH=src:/Users/icmini/0luka/tools python3 -m pytest -q tests/test_service.py tests/test_service_authoring_api.py`
- `PYTHONPATH=src:/Users/icmini/0luka/tools python3 -m pytest -q tests/test_authoring_flow.py tests/test_discipline_aggregation.py`
