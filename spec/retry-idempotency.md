# WCP Retry and Idempotency Semantics

**Companion to:** spec/1.0-rc1.md
**Status:** normative
**Compiled:** 2026-05-23

Network partitions, timeouts, and transient backend failures are routine in physical-world deployments. This document defines the idempotency contract per RPC so retries are safe.

## 1. Idempotency keys

Every RPC request MAY include `params.idempotency_key`, a client-chosen string up to 64 characters. If present, the coordinator MUST:

1. Look up a recent record (within an operator-defined window, default 24 hours) for the same `idempotency_key` from the same caller DID.
2. If found and the prior request's parameters match the current request's parameters byte-for-byte after canonical-JSON serialization, return the prior response without re-executing the operation.
3. If found but parameters differ, return `-32602 INVALID_PARAMS` with `data.symbol: wcp.error.idempotency_key_collision`.
4. If not found, execute the operation and record the response keyed by `idempotency_key`.

A coordinator MAY refuse `idempotency_key` reuse beyond the configured window; clients SHOULD generate fresh keys per logical operation.

## 2. Per-RPC idempotency table

| RPC | Native idempotency key | Notes |
|---|---|---|
| capabilities/list | (worker_id, revision) | Worker's monotonic `revision` is the natural key; coordinator de-duplicates by it |
| capabilities/subscribe | (agent_did, filter_canonical_hash, since_revision) | A fresh subscribe with identical filter and revision returns the existing subscription_id |
| tasks/post | (posted_by, idempotency_key) if provided, else (posted_by, hash(task_canonical_json)) | Repost with same body is idempotent and returns the original task_id |
| tasks/claim | (worker_id, task_id) | A second claim for the same (worker_id, task_id) returns the existing claim_id if accepted, or `TASK_PREEMPTED` if the worker lost the race |
| tasks/execute (open) | (claim_id) | Re-opening returns the existing session_id |
| tasks/execute event | (claim_id, event_id) where event_id is set by the worker | A duplicate event_id is silently de-duplicated |
| tasks/attest | (claim_id, idempotency_key) if provided, else (claim_id, hash(attestations_canonical)) | A second attest with identical attestations returns the cached verifier_decision |
| tasks/settle | (claim_id) | Settlement is once per claim; second call returns the original settlement_id |
| tasks/supervise | (claim_id, idempotency_key) | A second supervise request with identical params returns the existing supervisor session |
| tasks/abort | (claim_id) | Abort is once per claim; second call returns the original abort_id |

## 3. Retry semantics

Every error response includes `data.retry` per `error-codes.md`. The structure:

```json
"retry": {
  "retryable": true,
  "class": "transient",
  "retry_after_ms": 500,
  "max_attempts_recommended": 6
}
```

Clients SHOULD honor `retry_after_ms` and exponentially back off thereafter (e.g., 500ms, 1s, 2s, 4s, 8s, 16s) with full jitter. After `max_attempts_recommended` attempts, the client SHOULD surface the failure to the user rather than continue retrying.

## 4. claim_id reuse semantics

A `claim_id` is unique within the coordinator's scope and bound to one (task_id, worker_id) pair. The following operations are safe to retry against the same claim_id:

- tasks/execute (open) -> returns same session_id
- tasks/attest (with same attestations) -> returns same verifier_decision
- tasks/settle (after attesting) -> returns same settlement_id
- tasks/abort (after lifecycle entered abort path) -> returns same abort_id

Operations on a claim_id in a terminal state (settled, refunded, aborted) return `-42004 TASK_STATE_INVALID`.

## 5. Network-partition behavior

A worker that loses connectivity mid-execution and reconnects MUST:

1. Re-open the execute session via `tasks/execute(claim_id)`. The coordinator returns the existing session_id and recovered state.
2. Catch up by emitting a `state_snapshot` event with `event_type="reconnect_state"`, signed.
3. Resume heartbeats. If the coordinator transitioned to `supervising` due to missed heartbeats, the worker MUST call `tasks/supervise` to negotiate return (or `tasks/abort` if the worker cannot continue).

The coordinator MUST NOT discard a claim_id during a partition. The claim is reserved until the dispute window closes (default 72 hours from the most recent state change) or until explicit abort.

## 6. Idempotency under federation

For federated `tasks/post`, the federation envelope MUST carry `idempotency_key` if the origin agent supplied one. The peer coordinator de-duplicates per its own window and SHOULD respect the origin's idempotency intent.

For federated reputation queries, repeated queries within `reputation_summary.ttl_seconds` SHOULD return cached results.

## 7. Audit chain and idempotency

Audit chain entries are NOT created for idempotent no-op returns. An idempotency-key match returns the original entry's reference. This keeps the chain free of artifactual duplicate entries while preserving full history of distinct operations.

## 8. Conformance tests

The conformance suite Level 1 includes:

- Idempotency replay for tasks/post, tasks/claim, tasks/attest, tasks/settle.
- Idempotency key collision returns -32602 with the documented symbol.
- claim_id reuse across all retry-safe operations.

Level 2 adds:

- Network-partition recovery via execute re-open.
- Heartbeat-timeout to supervise to execute transition.
- Audit chain integrity preserved across retries.
