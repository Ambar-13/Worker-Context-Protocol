# RFC 0027: Rust SDK

- Author(s): TBD
- Status: open (v1.1 deliverable)
- Type: informational
- Created: 2026-05-23
- Targets: v1.1

## Summary

A Rust SDK (`wcp_sdk_rust/`) suitable for embedded and high-performance worker implementations. Async via tokio.

## Motivation

Robot firmware often uses Rust for the same reasons firmware historically used C: predictable performance, memory safety. A native Rust SDK avoids the FFI overhead of calling into a Python or C++ binding.

## Open design questions

- ed25519-dalek vs ring vs RustCrypto/ed25519.
- tokio vs async-std; how to remain runtime-agnostic where possible.
- no-std support for the most constrained targets.

## Implementation track

v1.1; ~2000 LOC budget.
