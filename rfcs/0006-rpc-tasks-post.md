# RFC 0006: RPC tasks/post

- Author(s): Rentably
- Status: accepted (part of v0.1); settlement-related portions amended at v0.955 (see `spec/0.955.md` — the descriptor's `settlement` block and the escrow-hold step are removed; new optional fields `max_attestation_attempts` and `marketplace_ref` apply).
- Type: standards-track
- Created: 2026-05-23

## Summary

`tasks/post` is the agent-initiated RPC submitting a TaskDescriptor with bonded escrow.

## Design

See `spec/0.1.md` Section 3.3.

Request: `{ task: TaskDescriptor, bond_ref, expiry, supervision? }`. Response: `{ task_id, eligible_workers_count, posted_at }`.

The coordinator MUST:
- Validate `task.attestation_requirement` against the schema registry (RFC 0003).
- Reject `x-subcontract-allowed=true` with `SUBCONTRACT_FORBIDDEN` (RFC 0002).
- Refuse out-of-scope task classes per `spec/0.1.md` Section 10.
- Place a two-phase escrow hold via the settlement adapter.

## Implementation track

`wcp_coordinator.tasks_service.post`. Adversarial tests in `test_adversarial_scenarios.py` cover Scenarios 8, 11, 13.
