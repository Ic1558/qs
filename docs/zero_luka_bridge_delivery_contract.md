# ZeroLuka Bridge Delivery Contract

## Purpose

This document freezes the delivery contract for handing `ZeroLukaBridgePayload` from QS into 0luka-side consumers.

This phase is specification-only.

In scope:
- define the delivery unit shape
- define accept/reject rules
- define duplicate and idempotency rules
- define ownership boundaries
- define failure classification

Out of scope:
- live bridge delivery
- Redis/pubsub
- queue workers
- event feed append
- proof generation
- watchdog integration
- filesystem or network transport

## Delivery Unit Shape

The stable bridge delivery unit is `ZeroLukaBridgePayload.to_dict()` output.

Top-level required fields:
- `kind`
- `bridge_kind`
- `run_id`
- `job_type`
- `project_id`
- `status`
- `payload`

Canonical shape:

```json
{
  "kind": "qs.runtime_result",
  "bridge_kind": "0luka.bridge_result",
  "run_id": "prj_601__boq_generate",
  "job_type": "qs.boq_generate",
  "project_id": "prj_601",
  "status": "completed",
  "payload": {
    "kind": "qs.runtime_result",
    "run_id": "prj_601__boq_generate",
    "job_type": "qs.boq_generate",
    "project_id": "prj_601",
    "status": "completed",
    "body": {}
  }
}
```

## Required vs Optional Fields

Required fields:
- `kind`
- `bridge_kind`
- `run_id`
- `job_type`
- `project_id`
- `status`
- `payload`

Optional top-level fields:
- none

Locked rules:
- `bridge_kind` must remain `0luka.bridge_result`
- `run_id` is the primary delivery idempotency anchor
- `status` must remain terminal only:
  - `completed`
  - `failed`
  - `rejected`
- `payload` must contain canonical `RuntimeTransportPayload.to_dict()` output

## Identity Integrity

The following fields must never be rewritten by delivery implementations:
- `run_id`
- `job_type`
- `project_id`
- `status`

QS guarantees those fields are preserved through contract generation.
0luka delivery and runtime layers must not mutate them.

## Accept / Reject Semantics

0luka bridge consumers should ACCEPT when:
- payload shape is valid
- `bridge_kind` equals `0luka.bridge_result`
- identity fields are present and well-formed
- `status` is terminal and valid
- `payload` is present and structurally valid

0luka bridge consumers should REJECT when:
- malformed top-level shape
- unexpected `bridge_kind`
- malformed identity
- non-terminal or unknown `status`
- missing `payload`

Reject means:
- do not consume into downstream runtime state
- do not treat the delivery unit as accepted

Reject handling and reporting belong to 0luka delivery/runtime layers, not QS.

## Duplicate / Idempotency Rules

Idempotency anchor:
- `run_id`

Rules:
- replaying the exact same delivery unit must not create divergent downstream state
- duplicate handling is a consumer/runtime responsibility
- QS guarantees deterministic construction, not delivery uniqueness enforcement beyond `run_id`
- no delivery layer should generate a new identity for the same bridge unit

## Failure Classification

Conceptual failure classes:

`contract-invalid`
- delivery unit shape invalid before consumption

`consumer-rejected`
- delivery unit syntactically valid enough to inspect, but rejected by consumer contract rules

`delivery-failed`
- transport mechanism failed before a valid consumer decision

`downstream-processing-failed`
- consumer accepted the delivery unit, but later runtime processing failed

Boundary rule:
- QS only covers contract-valid construction
- delivery failure, retry policy, dead-letter handling, and runtime processing failure belong outside QS

## Delivery Ownership Boundaries

QS owns:
- deterministic contract generation
- stable payload shapes
- identity preservation
- terminal status preservation

0luka delivery/runtime owns:
- transport mechanism
- retries
- acknowledgements
- dead-letter handling
- event feed append
- proof generation
- runtime persistence
- watchdog/supervision

## Allowed Future Enrichment

0luka may add later, outside QS:
- delivery timestamps
- ack metadata
- bridge processing markers
- proof/event references

Rules for enrichment:
- enrichments must not rewrite canonical QS identity fields
- enrichments must not rewrite canonical terminal status
- enrichments must remain additive outside the frozen QS payload identity

## Example Delivery Units

### Accepted Completed Delivery Unit

```json
{
  "kind": "qs.runtime_result",
  "bridge_kind": "0luka.bridge_result",
  "run_id": "prj_601__boq_generate",
  "job_type": "qs.boq_generate",
  "project_id": "prj_601",
  "status": "completed",
  "payload": {
    "kind": "qs.runtime_result",
    "run_id": "prj_601__boq_generate",
    "job_type": "qs.boq_generate",
    "project_id": "prj_601",
    "status": "completed",
    "body": {
      "run_id": "prj_601__boq_generate"
    }
  }
}
```

### Accepted Failed Delivery Unit

```json
{
  "kind": "qs.runtime_result",
  "bridge_kind": "0luka.bridge_result",
  "run_id": "prj_602__compliance_check",
  "job_type": "qs.compliance_check",
  "project_id": "prj_602",
  "status": "failed",
  "payload": {
    "kind": "qs.runtime_result",
    "run_id": "prj_602__compliance_check",
    "job_type": "qs.compliance_check",
    "project_id": "prj_602",
    "status": "failed",
    "body": {
      "outcome_classification": "failure"
    }
  }
}
```

### Accepted Rejected Delivery Unit

```json
{
  "kind": "qs.runtime_result",
  "bridge_kind": "0luka.bridge_result",
  "run_id": "prj_603__po_generate",
  "job_type": "qs.po_generate",
  "project_id": "prj_603",
  "status": "rejected",
  "payload": {
    "kind": "qs.runtime_result",
    "run_id": "prj_603__po_generate",
    "job_type": "qs.po_generate",
    "project_id": "prj_603",
    "status": "rejected",
    "body": {
      "outcome_classification": "rejection"
    }
  }
}
```

### Rejected Malformed Delivery Unit

```json
{
  "kind": "qs.runtime_result",
  "bridge_kind": "unexpected.bridge_kind",
  "run_id": "",
  "job_type": "qs.boq_generate",
  "project_id": "prj_999",
  "status": "running",
  "payload": null
}
```

Why rejected:
- unexpected `bridge_kind`
- malformed `run_id`
- non-terminal `status`
- missing valid `payload`

## Summary

This contract freezes how `ZeroLukaBridgePayload` is handed to 0luka consumers:
- deterministic shape
- terminal status only
- `run_id` as idempotency anchor
- accept/reject rules owned by 0luka consumers
- delivery, retries, proof, and persistence remain outside QS
