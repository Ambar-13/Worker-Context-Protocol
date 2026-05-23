# RFC 0007: RPC tasks/claim

- Author(s): Rentably
- Status: accepted (part of v0.1)
- Type: standards-track
- Created: 2026-05-23

## Summary

`tasks/claim` is the worker-initiated RPC claiming a posted task. Carries a signed `acceptance_attestation`.

## Design

See `spec/0.1.md` Section 3.4.

Request: `{ task_id, worker_id, bid?, eta, acceptance_attestation }`. Response: `{ claim_id, accepted, counter?, reason? }`.

`acceptance_attestation` is an Ed25519 signature over the canonical-JSON of `{task_id, worker_id, eta, bid, payload_hash, signed_at}`. The coordinator MUST verify the signature before mutating state.

Race semantics: first-claim-wins with a 100ms tie-break grace window for bid-based selection. Losers receive `accepted=false, reason="preempted"` (TASK_PREEMPTED).

Self-dealing check (Scenario 3): if `posted_by == worker.principal_id` and the task's attestation_requirement does not include `third-party-witness`, reject with `POLICY_VIOLATION`.

## Implementation track

`wcp_coordinator.tasks_service.claim`. Scenarios 3 and 4 covered in tests.
