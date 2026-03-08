# PLAN

- `trace_id`: `qs-authoring-docs-contracts-c451`
- `intent`: `authoring-docs-contracts`
- `executor`: `Codex IDE ([Lisa])`
- `level`: `L2`

## Goal

Land the next documentation-only PR for the authoring stack without mixing in runtime, service, UI, test, packaging, or generated-file noise.

## Scope

- `docs/ACCEPTANCE.md`
- `docs/ARCHITECTURE.md`
- `docs/AR_MEMBER_MODEL.md`

## Non-Goals

- `pyproject.toml`
- `src/`
- `tests/`
- `*.egg-info`
- build artifacts / caches / generated files

## Rule

Fail closed if the changed-files set contains anything outside the three docs above plus PR governance markdown under `ops/pr/authoring-docs-contracts/`.
