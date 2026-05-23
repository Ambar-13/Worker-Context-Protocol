# WCP Security Baseline

**Companion to:** spec/0.2.md
**Status:** normative
**Compiled:** 2026-05-23

This document defines the minimum security posture a conformant implementation MUST meet on the wire and in identity handling.

## 1. Transport

- **TLS 1.3 minimum.** TLS 1.2 MAY be supported for legacy compatibility but MUST NOT be the default and MUST be off by default.
- **`wss://` only.** Plain `ws://` is disallowed except in localhost development; conformance tests on localhost permit plain WS for harness convenience.
- **Required cipher suites (TLS 1.3):** TLS_AES_128_GCM_SHA256, TLS_AES_256_GCM_SHA384, TLS_CHACHA20_POLY1305_SHA256. Implementations SHOULD prefer TLS_AES_256_GCM_SHA384 and TLS_CHACHA20_POLY1305_SHA256 (the latter for mobile and embedded targets where AES hardware acceleration is unavailable).
- **Forbidden:** TLS_RSA_*, TLS_ECDH_*_WITH_NULL, TLS_NULL, anonymous ciphers.

## 2. Certificate validation

- Implementations MUST validate the server certificate against the system trust store or a configured pinned set.
- Self-signed certificates MAY be used in development with explicit pin configuration; production deployments MUST NOT accept self-signed.
- Certificate revocation MUST be checked via OCSP stapling or CRL where supported; soft-fail is acceptable for client-side robustness but MUST log the failure.

## 3. Origin and Host checks

- Coordinators MUST validate the `Host` header on incoming WS upgrade requests.
- Coordinators SHOULD support the `Origin` check for browser-based agents and reject mismatched origins with HTTP 403 before WS upgrade.
- Coordinators MUST NOT accept WS upgrade requests over plain HTTP except in localhost development.

## 4. Signature requirements per RPC

| RPC | Required signed by |
|---|---|
| capabilities/list | Worker (capability descriptor's signature, or session-level worker auth) |
| capabilities/subscribe | Agent |
| tasks/post | Agent |
| tasks/claim | Worker (`acceptance_attestation`); coordinator MUST verify before mutation |
| tasks/execute (open) | Worker (session level) |
| tasks/execute (events) | Worker (per-event signature in stream message) |
| tasks/attest | Worker (per-evidence signature) |
| tasks/supervise | Initiator (worker or coordinator) |
| tasks/abort | Initiator |

Audit chain entries are signed by the coordinator's audit signer (an Ed25519 key, typically HSM-backed in production).

## 5. Key management

- Worker key MUST be Ed25519. Other curves are not conformant at v0.2.
- Coordinator audit signing key MUST be Ed25519; production deployments SHOULD use an HSM or KMS-backed signer.
- Worker keys SHOULD be rotated on principal change or on suspicion of compromise. The `did:wcp` document key history supports rotation; see `did-method-wcp.md`.

## 6. Replay protection

- Each `acceptance_attestation` includes `signed_at` (ISO-8601). Coordinators MUST reject acceptance_attestations whose `signed_at` is older than 5 minutes from the coordinator's canonical time (per `time-synchronization.md`) or in the future by more than 30 seconds.
- Each evidence MUST include `collected_at`. Coordinators MUST reject evidence whose `collected_at` is in the future by more than 5 minutes, and SHOULD flag evidence older than 24 hours for review.
- Coordinators MUST de-duplicate by canonical-JSON hash within a 1-minute window per claim_id.

## 7. Rate limiting and backpressure

- Per-DID rate limits MUST be applied to every RPC. Defaults (overridable per operator):
  - capabilities/list: 60 per minute per worker
  - capabilities/subscribe: 10 active subscriptions per agent; 60 subscribe calls per hour
  - tasks/post: 60 per minute per agent (operator MAY raise)
  - tasks/claim: 600 per minute per worker
  - tasks/execute events: 600 per minute per claim (heartbeats are 4/min; rest is application)
  - tasks/attest: 10 per minute per claim
  - tasks/abort: 60 per minute per DID
- WebSocket backpressure: outbound send queue per connection capped at 64 messages; older messages MAY be dropped with a `wcp:queue_overflow` warning logged.

## 8. Input validation

- All inputs MUST be validated against the JSON Schema in `spec/schemas/` before any business logic.
- Maximum sizes (defaults):
  - TaskDescriptor: 64 KiB
  - CapabilityDescriptor: 32 KiB
  - AttestationEvidence: 16 KiB (sensor payloads remain device-side; only hashes leave)
  - Audit chain payload: 32 KiB
- Coordinators MUST reject payloads exceeding these with `INVALID_PARAMS`.

## 9. Logging and observability

- All security events (signature failures, rate-limit triggers, origin rejections, replay rejections) MUST be logged at WARN or ERROR.
- Logs MUST NOT include secret material, raw signatures (the audit chain entry id is sufficient), or PII fields tagged in `privacy-architecture.md`.
- OpenTelemetry-compatible structured logging is RECOMMENDED.

## 10. Vulnerability disclosure

See `SECURITY.md` at the repo root. The disclosure SLA is 90 days from first report to public disclosure; security-critical fixes MAY use the emergency RFC flag.

## 11. What this baseline does NOT cover

- Application-layer authorization between operator and consumer (operator responsibility).
- Cross-coordinator federation key management beyond trust anchor exchange (see `federation.md`).
- Physical security of worker devices (out of WCP scope).
- DDoS at the network or transport layer (operator infrastructure).
