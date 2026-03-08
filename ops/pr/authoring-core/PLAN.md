# PLAN

- `trace_id`: `qs-authoring-core-a9b1`
- `intent`: `authoring-core`
- `executor`: `Codex IDE ([Lisa])`
- `level`: `L3`

## Goal

Land the project-based authoring core as a clean first PR without pulling in HTTP service, UI, or doc refresh work that is still mixed in the main working tree.

## Scope

- Add project/takeoff storage, calculation, review, acceptance, aggregation, drawing-import, and workbook core modules.
- Extend `src/universal_qs_engine/api.py` with project-level authoring functions used directly by the new tests and proof script.
- Harden `src/universal_qs_engine/qs_engine_adapter.py` so `qs_engine` is resolved lazily at export time instead of import time.
- Add authoring-core tests and the phase 6 proof script.

## Out of Scope

- `src/universal_qs_engine/service.py`
- `src/universal_qs_engine/ui/*`
- docs refresh (`docs/ACCEPTANCE.md`, `docs/ARCHITECTURE.md`, `docs/AR_MEMBER_MODEL.md`)
- packaging metadata noise (`*.egg-info`)

## Risks

- The new API surface grows quickly and could accidentally become a service/UI PR if the scope is not locked.
- Export flows depend on `qs_engine`; import-time coupling would break clean-room test collection.
