# RFC 0011: RPC tasks/supervise

- Author(s): Rentably
- Status: accepted (part of v0.1)
- Type: standards-track
- Created: 2026-05-23

## Summary

`tasks/supervise` is the graded-autonomy handoff RPC. A worker (or the coordinator on heartbeat timeout) opens a supervisor session.

## Design

See `spec/0.1.md` Section 3.8.

Request: `{ claim_id, handoff_reason, state_snapshot, urgency }`. Response: `{ supervisor_id, session_url, takeover_authority: "advise" | "co_pilot" | "full" }`.

**The agent's contract does not move under the worker's feet** (Scenario 12). The `attestation_requirement` on the original `tasks/post` remains binding through supervision handoffs and across autonomy upgrades. If the worker cannot satisfy the original requirement, the only paths out are continued supervision or `tasks/abort`.

## Implementation track

`wcp_coordinator.tasks_service.supervise`. Test `test_scenario12_supervision_handoff_preserves_attestation_requirement` verifies that the requirement persists.
