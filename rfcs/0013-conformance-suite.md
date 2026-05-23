# RFC 0013: Conformance Suite

- Author(s): Rentably (principal)
- Status: accepted (part of v0.2)
- Type: standards-track
- Created: 2026-05-23
- Targets: v0.2, v1.0 final

## Summary

Defines the conformance suite as the canonical determinant of "WCP-conformant at Level N". The suite lives at `conformance/`. The Python runner is the v0.2 reference; a Go runner is targeted for v0.2 final.

## Motivation

A protocol is only as strong as its conformance test. Without a runnable test bundle, "WCP-conformant" becomes marketing. The suite makes the claim verifiable.

## Design

See `spec/conformance.md` (normative) and `conformance/levels.md` (test bundles).

## Drawbacks

A suite imposes maintenance burden on the steward. Adding new test cases requires care to avoid breaking existing passing implementations.

## Prior art

- W3C Web Platform Tests
- OpenID Foundation conformance suite
- TLS interop test labs

## Unresolved questions

- How to score performance conformance (orthogonal to functional levels) across heterogeneous hardware.
- How to certify federation conformance when no two coordinators in the test environment share trust anchors with a third.

## Implementation track

Python runner installable as `wcp-conformance`. Go runner placeholder under `conformance/runner-go/`.
