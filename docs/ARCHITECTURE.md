# QS Engine Architecture - Multi-Discipline Aggregation

This document summarizes the aggregation engine implemented in Phase 6.

## Multi-Discipline Flow

The engine now supports a unified takeoff flow for Structure (ST), Architecture (AR), and MEP.

### 1. Ingestion
Stateless entities from CAD/PDF extractions are mapped to stateful v2 members.
- **ST**: Beams, Slabs, Pedestals (Geometry-heavy)
- **AR**: Walls, Openings, Finishes, Area Blocks (Deduction-heavy)
- **MEP**: Counts, Runs, Risers (Aggregation-heavy)

### 2. Aggregation Engine
The `aggregation_engine.py` acts as a cross-discipline logic layer:
- **AR Wall Deductions**: Automatically calculates `net_area` for walls by deducting opening areas.
- **Finish Mapping**: Propagates wall `net_area` to dependent finish layers (Paint, Render, etc.).
- **MEP Auto-Seeding**: Converts MEP members (Runs/Counts) into calculation components automatically.

### 3. Calculation Graph
The `calc_graph.py` remains the single source of truth for quantities.
- Every row is tagged with its owning discipline.
- Deductions and overrides are preserved in the audit trail.

### 4. Acceptance Gates
Phase 5/6 extended the acceptance criteria to include:
- `ar_walls_closed`: Every wall must have positive net area.
- `mep_takeoff_closed`: Every MEP run/count must have positive quantity.
- Manual overrides are supported with mandatory justification.

## Bridge & Orchestration (Phase 7)

The QS Engine is integrated into the 0luka ecosystem via a bridge adapter.

### Task Dispatching
0luka core or Opal agents can submit a `qs.generate_boq` task. The `core/bridge.py` adapter automatically maps this intent to a `CLEC` operation that invokes the engine's CLI.

### Pipeline Execution
1. **Submit**: High-level task with `project_id`.
2. **Execute**: The `CLECExecutor` runs the CLI command in a sandboxed environment.
3. **Audit**: Results are captured, validated, and published to the task outbox.

### Unified Enforcement
The bridge command enforces the same cryptographic and metadata gates as the local SPA, ensuring no "shadow exports" bypass the governance layer.

## Implementation Principles
- **Hard Gate Priority**: `block_owner` flags (missing metadata) cannot be bypassed.
- **Traceability**: Every row traces back to `source_ref` and `basis_status`.
- **Fail-Open Calculation**: Incomplete geometry falls back to `DENSITY_FALLBACK` rather than crashing.
