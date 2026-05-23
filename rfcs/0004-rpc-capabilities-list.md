# RFC 0004: RPC capabilities/list

- Author(s): Rentably
- Status: accepted (part of v0.1)
- Type: standards-track
- Created: 2026-05-23

## Summary

`capabilities/list` is the worker-initiated RPC publishing a CapabilityDescriptor to the coordinator. Issued on registration, on capability change, and periodically per `ttl_seconds`.

## Design

See `spec/0.1.md` Section 3.1.

Request shape: `{}`. Response shape: `{ worker_id, capabilities: CapabilityDescriptor, ttl_seconds, revision }`.

`revision` is monotonic per worker; the coordinator increments on every successful upsert.

## Drawbacks

A worker re-publishing capabilities on every minor change creates churn. Mitigation: workers SHOULD batch capability updates and publish at most once per minute under normal operation.

## Prior art

MCP `tools/list` (informational; not directly inverted to this RPC but the in-band-discovery pattern is identical).

## Implementation track

`wcp_coordinator.capabilities_service.upsert_capabilities` and `.list_capabilities`. Tests in `wcp_coordinator/tests/test_d4_forcing_function.py` exercise across worker classes.
