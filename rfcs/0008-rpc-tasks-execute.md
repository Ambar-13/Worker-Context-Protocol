# RFC 0008: RPC tasks/execute

- Author(s): Rentably
- Status: accepted (part of v0.1)
- Type: standards-track
- Created: 2026-05-23

## Summary

`tasks/execute` opens a bidirectional execution session. The worker emits a stream of signed events; the coordinator records them in the audit chain.

## Design

See `spec/0.1.md` Section 3.5.

Request: `{ claim_id }`. Response: stream of `{ event_type, timestamp, payload, sig }`.

Heartbeat (Scenario 5): the worker MUST emit `heartbeat` every 15s. Three missed (45s) trigger automatic `executing -> supervising` with `handoff_reason="connectivity_lost"`. Reconnection with signed `state_snapshot` resumes execution.

Application-defined event types are permitted; v0.1 reserves `execution_started`, `picked_up`, `arrived_at_dropoff`, `checkpoint`, `heartbeat`, `supervision_tier_changed`.

## Implementation track

`wcp_coordinator.tasks_service.execute_open`, `.execute_event`, `.check_heartbeats`. Scenario 5 covered in `test_adversarial_scenarios.py`.
