# RFC 0005: RPC capabilities/subscribe

- Author(s): Rentably
- Status: accepted (part of v0.1)
- Type: standards-track
- Created: 2026-05-23

## Summary

`capabilities/subscribe` is the agent-initiated RPC opening a server-side stream of capability updates filtered by an opaque query.

## Design

See `spec/0.1.md` Section 3.2.

Request: `{ filter?, since_revision? }`. Response (one-shot): `{ subscription_id, stream_endpoint, ttl_seconds }`. Stream messages over `stream_endpoint`: `{ worker_id, capabilities, revision }`.

`since_revision` allows resumption after disconnect: the coordinator replays updates since that revision before live-tailing.

## Drawbacks

Long-lived subscriptions hold connections. Coordinators MUST bound the number of subscriptions per agent DID and SHOULD enforce backpressure.

## Implementation track

`wcp_coordinator.capabilities_service.create_subscription`. Streaming over `stream_endpoint` is application-layer at v0.1; v0.2 will define a normative stream framing.
