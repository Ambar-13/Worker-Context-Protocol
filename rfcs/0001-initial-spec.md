# RFC 0001: Initial v0.1 Specification

- Author(s): Rentably (principal)
- Status: accepted (frames the v0.1 spec as initial RFC)
- Type: standards-track
- Created: 2026-05-23
- Targets: v0.1

## Summary

This RFC adopts `spec/0.1.md`, `spec/did-method-wcp.md`, `spec/schemas/*.json`, and `spec/d4-verification.md` as the initial v0.1 specification of the Worker Context Protocol.

## Motivation

WCP needs a versioned, citable starting point. RFC 0001 binds the v0.1 surface so that subsequent RFCs may reference it. Without RFC 0001 the spec drifts.

## Design

- The nine RPCs of `spec/0.1.md` Section 3 are normative.
- The CapabilityDescriptor, TaskDescriptor, AttestationEvidence, AuditChainEntry JSON Schemas in `spec/schemas/` are normative.
- The `did:wcp` method spec in `spec/did-method-wcp.md` is normative.
- The D4 verification in `spec/d4-verification.md` is informative.
- The operational defaults from `spec/0.1.md` Section 11 (heartbeat 15s, three missed; bid tie-break 100ms; dispute window 72h) are normative.

## Drawbacks

Locking the surface forecloses some design space (e.g., subcontracting; see RFC 0002). The tradeoff is intentional per PLAN.md D4.

## Alternatives

- Publish without versioning. Rejected: makes spec evolution untraceable.
- Publish with multiple parallel versions. Rejected: confuses early adopters.

## Prior art

MCP shipped v0.1 with its protocol document and reference servers under one initial release. WCP follows the same model.

## Unresolved questions

None for v0.1.

## Implementation track

Reference implementations (FastAPI backend, ROS 2 plugin, PWA module) ship simultaneously with this RFC.
