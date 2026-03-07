# Architecture

## Intent

The repo is a thin implementation blueprint for a Universal QS engine that 0luka can load as a candidate module.

## Pipeline

```text
Input Manager
  -> PDF / DWG / DXF intake
  -> normalization into universal element schema
  -> discipline logic stubs
     -> architecture: net area deductions
     -> structure: volume + rebar density
     -> mep: path length + fittings + riser injection
  -> BOQ planning
     -> PO-4 detailed proofs
     -> PO-5 pricing rollup
     -> PO-6 Factor F summary
  -> audit/export planning
```

## Runtime Surfaces

- `universal_qs_engine.pipeline`: deterministic preview builder
- `universal_qs_engine.api`: deterministic module endpoint handlers that mirror the expanded spec
- `universal_qs_engine.optimizer`: cheap-first planning for lower-cost execution paths
- `universal_qs_engine.workbook`: PO-4 / PO-5 / PO-6 template metadata and named ranges
- `universal_qs_engine.service`: stdlib HTTP service with `/api/health` and module endpoints
- `universal_qs_engine.cli`: command-line wrapper for local runs and launchd

## Current Boundary

This scaffold does not implement OCR, DWG parsing, or XLSX generation yet. It now defines the endpoint contracts, workbook structure, fallback rules, and final gate semantics needed to start Phase 1 without coupling the repo to 0luka internals.
