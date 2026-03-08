# PLAN

- `trace_id`: `qs-authoring-api-ui-b732`
- `intent`: `authoring-api-ui`
- `executor`: `Codex IDE ([Lisa])`
- `level`: `L3`

## Goal

Expose the authoring-core project workflow over HTTP and the local workspace UI without mixing in the still-pending docs/contract refresh.

## Scope

- wire project authoring functions into `src/universal_qs_engine/service.py`
- replace the old intake/review UI with the authoring workspace under `src/universal_qs_engine/ui/`
- add service-layer regression tests for v2 routes and static workspace delivery

## Out of Scope

- docs refresh in `docs/`
- packaging metadata noise (`*.egg-info`)
- additional domain-core changes already packaged in PR #2

## Stacking

This PR is intentionally stacked on top of `codex/feat-authoring-core-a9b1` / [Ic1558/qs#2](https://github.com/Ic1558/qs/pull/2).
