# RFC 0021: Retry and Idempotency Semantics

- Author(s): Rentably (principal)
- Status: accepted (part of v1.0-rc1)
- Type: standards-track

## Summary

Adopts `spec/retry-idempotency.md`: optional `params.idempotency_key`, per-RPC idempotency keys (natural keys per the table), structured retry semantics (`retry.retryable`, `retry.class`, `retry.retry_after_ms`), network-partition recovery via execute re-open.

## Drawbacks

The 24-hour idempotency-window default is arbitrary and may be too short for some operators (long-running disputes). Mitigation: operator MAY widen the window via configuration; conformance tests use 1-hour windows.

## Prior art

- Stripe API idempotency keys
- Kubernetes resource version semantics
- AWS SDK retry conventions

## Implementation track

`retry-idempotency.md` is the artifact. The SDK exposes `idempotency_key` as an optional field on relevant RPCs. The conformance suite Level 1 exercises 4 idempotency cases (tasks/post, tasks/claim, tasks/attest, tasks/settle).
