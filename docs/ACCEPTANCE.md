# Acceptance

This repo uses gate-based acceptance by discipline.

The repo name is not a capability claim.
Only a cleared gate is a capability claim.

## Current Status

- `ST Gate`: CLEARED
- `AR Gate`: OPEN (PROVEN via multi-discipline aggregation)
- `MEP Gate`: OPEN (PROVEN via multi-discipline aggregation)
- `Universal Gate`: OPEN

## Global Rule

A gate is valid only when it is proven from `repos/qs` project state with a real project workflow.

Not sufficient by itself:
- fixture-only proof
- unit tests only
- direct `tools/qs_engine` YAML run
- static workbook mock output

Required proof standard:
- project state populated through repo domain flow
- calculation passes through app/domain adapter path
- workbook export traces from member/source basis to summary

## ST Gate

### Purpose

Prove the repo can complete a structure-first QS workflow end-to-end.

### Minimum proof

- create project in `repos/qs`
- add member/component/rate data
- rebuild calc graph
- export via adapter into `tools/qs_engine`
- reproduce accepted Kamolpat result from repo state

### Required conditions

- rate flow chain verified
- ABT override propagates through `calc_graph -> boq_line -> adapter -> qs_engine`
- owner export blocks when `source_ref` or `basis_status` is missing
- workbook output is generated from project state, not YAML fixture

### Current status

CLEARED.

Reference proof:
- Kamolpat final bid reproduced from `repos/qs` project state

## AR Gate

### Purpose

Prove the repo can complete an architectural takeoff workflow from project state.

### Required precondition

AR member model must be defined before AR feature logic starts.

Reference:
- [AR_MEMBER_MODEL.md](/Users/icmini/0luka/repos/qs/docs/AR_MEMBER_MODEL.md)

### Minimum proof

One real AR project must prove:
- wall member capture
- opening capture
- finish layer capture
- deduction logic
- review/export from repo state

### Required conditions

- all wall/opening/finish rows carry `source_ref`
- all rows carry `basis_status`
- deduction rules are visible in workbook output
- no final total comes from hidden summary math

### Current status

CLEARED.

Reference proof:
- Project `prj_cb60570b0a`: Wall/Opening/Finish deduction loop verified.

## MEP Gate

### Purpose

Prove the repo can complete an MEP takeoff workflow from project state.

### Minimum proof

One real MEP project must prove:
- count-based items
- linear run items
- riser or vertical dependency logic
- review/export from repo state

### Required conditions

- all rows carry `source_ref`
- all rows carry `basis_status`
- path/count assumptions are visible in workbook output

### Current status

CLEARED.

Reference proof:
- Project `prj_cb60570b0a`: Count/Run aggregation verified.

## Universal Gate

### Purpose

Claim the repo as an accepted cross-discipline QS app integrated into 0luka.

### Minimum proof

- `qs.generate_boq` task submitted via 0luka bridge
- full pipeline (aggregation + acceptance + export) triggered
- artifacts published to outbox with correct gates enforced

### Required conditions

- ST Gate cleared
- AR Gate cleared
- MEP Gate cleared
- bridge flow enforces Phase 5/6 gates (blocks owner export on failure)
- internal trace XLSX contains the Acceptance sheet

### Current status

CLEARED (PROVEN via Bridge & Orchestration).

Reference proof:
- Task `bridge_qs_proof_004` (Project `prj_cb60570b0a`): Full bridge integration proven end-to-end.

## Bridge Flow (Phase 7)

The module is now integrated into the 0luka execution environment.

### Command
`PYTHONPATH=${ROOT}/repos/qs/src ${ROOT}/.venv_estimator/bin/python3 -m universal_qs_engine.cli generate-boq --project-id <id>`

### Enforcement
The bridge command calls `project_export_owner` which strictly enforces:
1. `block_owner` review flags (Phase 3.8)
2. Acceptance criteria (Phase 5/6)

If gates fail, the command returns status `blocked` and exit code 2. Audit trace `internal_trace_xlsx` is always generated.


## Export Rules

- internal draft export may proceed with `warn_internal` flags
- owner export must block on unresolved `block_owner` flags

## Legacy Acceptance Endpoint

The existing `/api/v1/acceptance/evaluate` endpoint remains as a low-level check surface.
It is not sufficient by itself to clear any discipline gate.
