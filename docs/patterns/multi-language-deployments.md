# Pattern: Multi-Language Deployments

How to run a WCP deployment where the coordinator, agents, and workers are implemented in different languages. WCP is wire-protocol-defined (JSON-RPC 2.0 over WebSocket), so mixing languages is the norm rather than the exception, but operators benefit from a small set of conventions to avoid integration friction.

## What "multi-language" looks like in practice

A typical real deployment:

- Coordinator: Python (the reference impl, `wcp_coordinator/`) OR Rust OR Go
- Agents: TypeScript (orchestration backends), Python (research scripts), Go (high-throughput dispatch)
- Workers: Rust (autonomous robots), C++ (legacy industrial), Python (research instruments), TypeScript (browser-based teleoperation)

Each side picks the language that fits its constraints. The protocol's role is to make them interoperate.

## What the protocol promises (across all languages)

1. **Wire format is identical.** JSON-RPC 2.0 over WebSocket with the schemas in `spec/schemas/`. Any conforming implementation in any language produces and accepts the same byte sequences.

2. **Schema validation is portable.** All schemas are JSON Schema 2020-12. Every mainstream language has a validator.

3. **DIDs and keys are language-neutral.** `did:wcp` resolution returns a JSON document; Ed25519 signature verification is the same across languages.

4. **Audit chain entries are canonicalised before hashing.** RFC 8785 (JCS) canonical JSON is implemented in every language. The chain produced by a Python coordinator verifies in a TypeScript audit tool.

## What each language SDK MUST get right

The four shipped SDKs (Python `wcp_sdk`, TypeScript `@wcp/sdk`, Rust `wcp-sdk`, Go `wcp-go`) all guarantee:

- Canonical JSON serialisation matching JCS for any object that flows into a signature
- UTC timestamps with `T` separator and `Z` suffix (no offsets, no localised forms)
- Ed25519 signing and verification using the language's primary crypto library
- WebSocket reconnection with exponential backoff and jitter per RFC 0021
- Heartbeat keepalive interval and miss threshold matching the coordinator's policy

A new SDK in a language not yet shipped MUST meet the same guarantees. The conformance suite (`conformance/test-suite/`) is the gating check.

## Language choice considerations

| Concern | Recommended language |
|---|---|
| Coordinator at production scale | Rust or Go (memory-safe, high concurrency, mature WebSocket libraries) |
| Coordinator for research/prototyping | Python (fastest iteration; the reference impl) |
| High-throughput agent | Go or Rust |
| LLM-orchestrated agent | Python or TypeScript (best ecosystem for LLM clients) |
| Autonomous robot worker | C++ (existing robot stacks) wrapped in a Rust or Python WCP bridge |
| Browser-based teleoperation worker | TypeScript (only realistic choice) |
| Embedded sensor worker | Rust (no_std friendly) OR a C wrapper around a small reference implementation |

These are reasoned defaults; deployments diverge for good reasons.

## Cross-language data shapes that bite

Three places where languages differ enough to cause bugs if not handled carefully:

### 1. Numbers

JSON does not distinguish int from float. A WCP `settlement.amount` is a string (`"8.50"`) precisely to avoid this; the field type is `string` in every schema. Operators MUST not parse amount as a JSON number; that loses precision.

Other numeric fields (timestamps as unix epoch, latency in milliseconds) are integers; the schemas constrain them to `"type": "integer"`. Languages with arbitrary-precision integers (Python) and languages with fixed-size integers (Rust, Go, C) MUST agree on the same range. WCP integer fields are in i64 range.

### 2. Timestamps

All timestamps in WCP are RFC 3339 ISO-8601 strings: `2026-05-23T11:30:00Z`. Always UTC, always with `Z` suffix, always to second precision (sub-second permitted; six-digit fraction maximum). Languages that default to a different timestamp format MUST canonicalise on serialisation.

Common pitfalls:
- JavaScript `Date.toISOString()` produces `2026-05-23T11:30:00.000Z`; fine, sub-second permitted.
- Python `datetime.isoformat()` without `timespec="seconds"` produces six-digit microseconds; also permitted, but unstable across re-parse if downstream tooling reformats. Use `timespec="seconds"` for cleanest output.
- Go's `time.Time.Format(time.RFC3339)` produces a `+00:00` offset rather than `Z`. Use `time.RFC3339Nano` or post-process to substitute `Z`.

### 3. UTF-8 and string normalization

WCP strings are unrestricted UTF-8. Two strings that look the same but differ in Unicode normalization (precomposed vs decomposed) are NOT equal in JSON or signatures. JCS does not normalize. Operators dealing with international content MUST decide on a normalization form (NFC is the default recommendation) and apply it consistently *before* signing.

## DID resolution: same answer in every language

`did:wcp:<id>` resolution produces a JSON DID Document. Every SDK ships a resolver that returns the same document for the same input, byte-for-byte. The byte-for-byte property matters when the DID document itself is hashed into an audit chain entry.

## Audit chain verification: language-agnostic

The audit chain's hash links are SHA-256 of the canonicalised entry JSON. A verifier in Python and a verifier in Rust produce the same digest for the same entry. This is the property that lets a forensic auditor verify a chain produced by a foreign coordinator without trusting the coordinator's tooling.

## Federation across language-different coordinators

Two coordinators implemented in different languages federate the same way as two coordinators in the same language: they exchange signed trust anchors, they emit signed audit chain entries, they accept each other's signed evidence. The wire-level interop is identical because the protocol is identical.

The friction in cross-language federation is operational, not protocol-level: operators run different on-call rotations, log to different systems, monitor with different tools. Federation agreements should explicitly cover these operational interfaces.

## Coordinator-side polyglot considerations

Some deployments run multiple coordinator processes for HA. The standard pattern is "same language, multiple replicas behind a load balancer." Mixing languages in a single coordinator's HA tier is technically possible but operationally fragile:

- Storage schemas vary between language SDKs (Python coordinator uses one Postgres schema; Rust might use a slightly different one)
- Hot-path performance differs; uneven load distribution under bursty traffic
- Operational tooling (migration scripts, backup tools, monitoring dashboards) is per-language

The right answer is usually: pick one language for the coordinator tier; mix freely on the agent and worker sides.

## What we don't ship and what to do instead

| Want | Reality | Workaround |
|---|---|---|
| Polyglot transactions | Not provided; each language SDK speaks the wire protocol independently | The wire protocol IS the contract; there is no shared in-memory state across SDKs |
| Shared logger | Not provided | Each SDK logs in its own conventions; aggregate with a structured log shipper (Loki, Datadog, etc.) |
| Code generation from spec | Not yet provided | Hand-written SDKs for the four shipped languages; community contributions welcome |

## See also

- `wcp_sdk_python/` Python SDK
- `wcp_sdk_typescript/` (TypeScript SDK shipped per RFC 0026)
- `wcp_sdk_rust/` (Rust SDK shipped per RFC 0027)
- `wcp_sdk_go/` (Go SDK shipped per RFC 0028)
- `rfcs/0017-semver-policy.md` for the versioning compatibility commitments across SDKs
- `rfcs/0021-retry-idempotency.md` for reconnect behavior all SDKs must implement
- `spec/canonical-json.md` for the JCS canonicalisation rules every SDK obeys
