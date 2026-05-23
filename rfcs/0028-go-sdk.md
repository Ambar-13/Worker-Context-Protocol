# RFC 0028: Go SDK

- Author(s): TBD
- Status: open (v1.1 deliverable)
- Type: informational
- Created: 2026-05-23
- Targets: v1.1

## Summary

A Go SDK (`wcp_sdk_go/`) for backend integrators. Idiomatic, context-aware.

## Motivation

Backend agents and operator-side tooling often use Go. A native SDK reduces friction for teams already on Go.

## Open design questions

- crypto/ed25519 (standard library) vs filippo.io/edwards25519 for advanced primitives.
- Idiomatic API shape: option functions vs config struct.
- gRPC vs JSON-RPC over WS (the spec mandates JSON-RPC over WS; the SDK could expose either at the public API level).

## Implementation track

v1.1; ~1500 LOC budget; pkg.go.dev-ready.
