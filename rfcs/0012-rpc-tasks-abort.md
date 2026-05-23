# RFC 0012: RPC tasks/abort

- Author(s): Rentably
- Status: accepted (part of v0.1); settlement-related portions amended at v0.955 (see `spec/0.955.md` — the `proposed_settlement` request field and the `settlement_disposition` response field are removed; the abort body shape becomes `{claim_id, reason, state_snapshot}` with response `{abort_id}`).
- Type: standards-track
- Created: 2026-05-23

## Summary

`tasks/abort` cancels a claim mid-lifecycle with a named reason and a proposed settlement disposition.

## Design

See `spec/0.1.md` Section 3.9.

Request: `{ claim_id, reason, state_snapshot, proposed_settlement: "split" | "refund" | "dispute" }`. Response: `{ abort_id, settlement_disposition: "applied" | "disputed" }`.

`split` invokes the `partial_completion_schedule` if present on the TaskDescriptor; default 50% release on accepted abort.

`refund` returns held funds to the agent.

`dispute` parks the claim in `disputed` state; out-of-band resolution closes.

## Implementation track

`wcp_coordinator.tasks_service.abort`. Lifecycle and partial settlement paths covered in tests.
