# Runtime Integration Contract

## Purpose

This document freezes the downstream runtime integration contract for `RuntimeTransportPayload`.

Scope:
- define the canonical payload schema
- define required and optional fields
- define status semantics
- define error propagation boundaries
- define idempotency and identity integrity rules

Non-scope:
- no live queue wiring
- no dispatcher implementation
- no network transport
- no filesystem persistence
- no 0luka imports

## Canonical Payload Schema

`RuntimeTransportPayload` is the stable downstream transport shape produced from `QueueResultMessage`.

Top-level required fields:
- `kind`
- `run_id`
- `job_type`
- `project_id`
- `status`
- `body`

Canonical shape:

```json
{
  "kind": "qs.runtime_result",
  "run_id": "prj_401__boq_generate",
  "job_type": "qs.boq_generate",
  "project_id": "prj_401",
  "status": "completed",
  "body": {
    "run_id": "prj_401__boq_generate",
    "job_type": "qs.boq_generate",
    "project_id": "prj_401",
    "status": "completed",
    "outcome_classification": "success",
    "requires_approval": false,
    "envelope_payload": {}
  }
}
```

## Required vs Optional Fields

Required top-level fields:
- `kind`
- `run_id`
- `job_type`
- `project_id`
- `status`
- `body`

Optional top-level fields:
- none

Required `body` rule:
- `body` must contain the exact `QueueResultMessage.to_dict()` output

Optional `body` fields:
- none at this layer; optionality is inherited from the already-built `QueueResultMessage` contract

## Field Constraints

### `kind`
- constant string identifier
- current required value: `qs.runtime_result`
- consumers must reject any unexpected `kind`

### `run_id`
- required
- must be globally unique within the consuming runtime domain
- must remain unchanged from `RunManifest`

### `job_type`
- required
- must match a known `job_contracts` type
- must remain unchanged through every adapter layer

### `project_id`
- required
- identifies QS project context
- must remain unchanged through every adapter layer

### `status`
- required
- terminal status only
- allowed values:
  - `completed`
  - `failed`
  - `rejected`

### `body`
- required
- must be `QueueResultMessage.to_dict()` output
- must not be rewritten into an alternative flattened shape by downstream consumers

## Status Semantics

`completed`
- job succeeded
- downstream runtime may consume outputs as successful terminal result

`failed`
- job executed but produced an error outcome
- downstream runtime must preserve failure semantics and must not coerce to success

`rejected`
- contract or validation failure
- downstream runtime must preserve rejection semantics and must not reinterpret as execution failure

Rules:
- `status` must always be terminal before `RuntimeTransportPayload` exists
- no runtime is allowed to mutate `status` after payload creation

## Error Propagation Rules

Invalid payload shape:
- reject

Unknown `job_type`:
- reject

Malformed identity fields:
- reject

Unexpected `kind`:
- reject

Transport-level failures:
- handled outside QS
- retries, dead-letter handling, delivery guarantees, and runtime ack behavior are downstream responsibilities

QS responsibilities stop at deterministic payload creation.

## Idempotency Guarantees

`RuntimeTransportPayload` is immutable.

Consumers must treat messages as idempotent by `run_id`.

Rules:
- replaying the same payload must not produce different state transitions
- payload reprocessing must not require QS to regenerate different content
- no adapter is allowed to add ambient timestamps, random values, or runtime-generated IDs

## Identity Integrity

The following fields must remain unchanged from `RunManifest` through all layers:
- `run_id`
- `job_type`
- `project_id`

No adapter or runtime is allowed to rewrite those fields.

## Transport Envelope Boundaries

Layer boundary:
- `RuntimeTransportPayload` is the last QS-owned translation layer
- live queue/runtime delivery happens outside QS

What this payload includes:
- stable identity
- terminal status
- canonical downstream body

What this payload does not include:
- queue routing metadata
- retry counters
- ack receipts
- network addressing
- storage references external to the existing payload body

## Consumer Acknowledge / Reject Semantics

Downstream runtimes should implement consume-time decisions as:

Accept:
- payload shape valid
- `kind` recognized
- `status` terminal and recognized
- identity fields present and non-empty

Reject:
- malformed top-level shape
- malformed or missing identity
- unexpected `kind`
- unknown `job_type`
- non-terminal `status`
- malformed `body`

QS does not define transport retry behavior.
QS does not define ack persistence behavior.
QS does not define backoff or redelivery behavior.

## Example Payloads

### Completed

```json
{
  "kind": "qs.runtime_result",
  "run_id": "prj_401__boq_generate",
  "job_type": "qs.boq_generate",
  "project_id": "prj_401",
  "status": "completed",
  "body": {
    "run_id": "prj_401__boq_generate",
    "job_type": "qs.boq_generate",
    "project_id": "prj_401",
    "status": "completed",
    "outcome_classification": "success",
    "requires_approval": false,
    "envelope_payload": {
      "run_id": "prj_401__boq_generate",
      "job_type": "qs.boq_generate",
      "project_id": "prj_401",
      "status": "completed"
    }
  }
}
```

### Failed

```json
{
  "kind": "qs.runtime_result",
  "run_id": "prj_402__compliance_check",
  "job_type": "qs.compliance_check",
  "project_id": "prj_402",
  "status": "failed",
  "body": {
    "run_id": "prj_402__compliance_check",
    "job_type": "qs.compliance_check",
    "project_id": "prj_402",
    "status": "failed",
    "outcome_classification": "failure",
    "requires_approval": false,
    "envelope_payload": {
      "run_id": "prj_402__compliance_check",
      "job_type": "qs.compliance_check",
      "project_id": "prj_402",
      "status": "failed",
      "error_code": "compliance_failed"
    }
  }
}
```

### Rejected

```json
{
  "kind": "qs.runtime_result",
  "run_id": "prj_404__po_generate",
  "job_type": "qs.po_generate",
  "project_id": "prj_404",
  "status": "rejected",
  "body": {
    "run_id": "prj_404__po_generate",
    "job_type": "qs.po_generate",
    "project_id": "prj_404",
    "status": "rejected",
    "outcome_classification": "rejection",
    "requires_approval": true,
    "envelope_payload": {
      "run_id": "prj_404__po_generate",
      "job_type": "qs.po_generate",
      "project_id": "prj_404",
      "status": "rejected",
      "error_code": "run_rejected"
    }
  }
}
```

## Summary

This contract freezes the QS downstream runtime payload at a narrow translation boundary:
- terminal status only
- immutable identity
- deterministic body
- no live transport behavior inside QS
