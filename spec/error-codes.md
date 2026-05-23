# WCP Error Code Taxonomy

**Companion to:** spec/1.0-rc1.md
**Status:** normative
**Compiled:** 2026-05-23

Errors are returned as JSON-RPC 2.0 error objects with `code`, `message`, and `data`. Codes are partitioned by category. Symbols are namespaced under `wcp.error`. Messages are English; i18n message keys live in `data.i18n_key`. Structured retry semantics live in `data.retry` per `retry-idempotency.md`.

## Error object shape

```json
{
  "code": -41001,
  "message": "Attestation requirement invalid: M > N (5 > 2)",
  "data": {
    "symbol": "wcp.error.invalid_attestation_requirement",
    "i18n_key": "wcp.error.invalid_attestation_requirement",
    "field_path": "task.attestation_requirement.M",
    "retry": {
      "retryable": false,
      "class": "permanent"
    },
    "audit_chain_entry": "<entry_id, if recorded>"
  }
}
```

`data.retry.class` is one of:

- `transient`: the operation MAY succeed on retry after `retry_after_ms`.
- `permanent`: the operation will not succeed without input change.
- `partial`: the operation partially succeeded; `data.partial_state` describes what was applied.

## Categories

### -32xxx: Standard JSON-RPC

| Code | Symbol | When |
|---|---|---|
| -32700 | wcp.error.parse_error | JSON parse failure |
| -32600 | wcp.error.invalid_request | Not a valid JSON-RPC 2.0 request envelope |
| -32601 | wcp.error.method_not_found | Method does not exist |
| -32602 | wcp.error.invalid_params | Schema validation failed |
| -32603 | wcp.error.internal_error | Coordinator bug; report with audit_chain_entry |

### -40xxx: Identity

| Code | Symbol | When |
|---|---|---|
| -40001 | wcp.error.unauthenticated | Missing or invalid signature |
| -40002 | wcp.error.unauthorized | DID resolved; role insufficient for operation |
| -40003 | wcp.error.did_not_resolved | DID is malformed or method-unknown |

### -41xxx: Attestation

| Code | Symbol | When |
|---|---|---|
| -41001 | wcp.error.invalid_attestation_requirement | M > N, unknown mode, or unknown kind in evidence_schema |
| -41002 | wcp.error.attestation_failed | Submitted evidence did not meet threshold |
| -41003 | wcp.error.attestation_review | Submitted evidence requires human review |
| -41004 | wcp.error.attestation_override_audit | Override invoked; audit chain entry pending |

### -42xxx: Task lifecycle

| Code | Symbol | When |
|---|---|---|
| -42001 | wcp.error.task_not_found | task_id or claim_id unknown |
| -42002 | wcp.error.task_preempted | Another worker claimed first (within 100 ms grace) |
| -42003 | wcp.error.task_expired | expiry passed before action |
| -42004 | wcp.error.task_state_invalid | Operation invalid in current state |

### -43xxx: Execution

| Code | Symbol | When |
|---|---|---|
| -43001 | wcp.error.heartbeat_timeout | Three missed heartbeats; auto-supervising |
| -43002 | wcp.error.worker_lost | Supervision window expired without reconnect |

### -44xxx: Settlement

| Code | Symbol | When |
|---|---|---|
| -44001 | wcp.error.settlement_failed | Escrow provider refused capture |
| -44002 | wcp.error.settlement_disputed | Dispute opened within dispute_window |
| -44003 | wcp.error.settlement_refunded | Refund applied per disposition |

### -45xxx: Scope

| Code | Symbol | When |
|---|---|---|
| -45001 | wcp.error.subcontract_forbidden | x-subcontract-allowed=true; not conformant at v1.0-rc1 |
| -45002 | wcp.error.out_of_scope_task_class | Task tagged for medical, defense, minor-involving, or hazmat-above-consumer |

### -46xxx: Policy

| Code | Symbol | When |
|---|---|---|
| -46001 | wcp.error.policy_violation | Operator policy refused the operation (e.g., self-dealing without third-party witness) |

### -5xxxx: Federation

| Code | Symbol | When |
|---|---|---|
| -50001 | wcp.error.federation_peer_unknown | Peer DID has no current trust anchor |
| -50002 | wcp.error.federation_trust_insufficient | Trust class not in mutual set |
| -50003 | wcp.error.federation_peer_unreachable | Network failure to peer |
| -50004 | wcp.error.federation_reputation_stale | Cross-coordinator reputation expired |
| -50005 | wcp.error.federation_audit_verification_failed | Peer audit chain signature invalid |
| -50006 | wcp.error.federation_jurisdiction_refused | Peer in non-compliant jurisdiction per local policy |

### -6xxxx: Conformance

| Code | Symbol | When |
|---|---|---|
| -60001 | wcp.error.conformance_level_unsupported | Implementation declares lower level than the call requires |
| -60002 | wcp.error.conformance_suite_version_unsupported | Implementation reports against an unsupported suite version |

### -7xxxx: Reserved for v1.1 (per RFCs 0022-0030)

### -8xxxx: Operator-defined (not WCP-normative)

Operators MAY define error codes in this range for their internal use. WCP clients MUST treat these as opaque errors with `data.symbol` providing the operator-specific symbol.

### -9xxxx: Reserved

## Retryability table

| Code prefix | Default retryable | Default class |
|---|---|---|
| -32xxx (except -32603) | no | permanent |
| -32603 | yes | transient (after backoff) |
| -40xxx | no | permanent (caller MUST refresh credentials) |
| -41001 | no | permanent (fix the requirement) |
| -41002 | no | permanent (collect different evidence and re-attest) |
| -41003 | yes | transient (after human review completes) |
| -41004 | yes | transient (after override is recorded) |
| -42001 | no | permanent |
| -42002 | no | permanent (task already lost) |
| -42003 | no | permanent |
| -42004 | depends on state | partial or permanent |
| -43001 | yes | transient (after reconnect) |
| -43002 | no | permanent |
| -44001 | yes | transient (after escrow recovery) |
| -44002 | no | partial (dispute resolution required) |
| -44003 | no | partial |
| -45xxx | no | permanent |
| -46001 | no | permanent (operator policy change required) |
| -50xxx | depends | varies (transient for unreachable; permanent for trust-insufficient) |
| -60xxx | no | permanent |

## Internationalization

Every error returned by a conformant coordinator MUST include `data.i18n_key` matching the symbol. Translation tables for the keys live in `docs/i18n/` (not normative; reference). Clients translate per their locale; the coordinator's `message` is always English for log/operator parity.

## Logging requirement

Coordinators MUST log every emitted error with:

- timestamp (per `time-synchronization.md`)
- DID of the caller (if authenticated)
- RPC method
- code, symbol
- audit_chain_entry (if a chain entry was recorded)
- a correlation id (per request)

Errors that include `retry.retryable=true` MUST include `retry.retry_after_ms` (>= 100, <= 60000).
