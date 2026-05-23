# RFC 0019: Security Baseline

- Author(s): Rentably (principal)
- Status: accepted (part of v0.2)
- Type: standards-track

## Summary

Adopts `spec/security-baseline.md`: TLS 1.3 minimum, wss:// only, origin checks, signature requirements per RPC, replay protection (5 minutes acceptance_attestation window), rate limits with default values per role, key management (Ed25519 worker keys; HSM-backed coordinator signing keys).

## Drawbacks

The strict TLS 1.3 floor cuts off some embedded targets without TLS 1.3 capability. Mitigation: implementations that cannot do TLS 1.3 MAY use a TLS-terminating proxy.

## Prior art

- TLS BCP from the IETF (RFC 9325)
- OWASP API Security Top 10
- Stripe and similar payment-API security postures

## Implementation track

`security-baseline.md` is the artifact. Conformance suite Level 1 checks signature requirements on tasks/claim, tasks/execute events, and tasks/attest. TLS configuration is implementation-side; the conformance harness MAY warn but does not block.
