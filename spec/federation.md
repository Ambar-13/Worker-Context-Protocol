# WCP Federation Primitives

**Companion to:** spec/0.2.md and spec/0.955.md
**Status:** normative. Updated at v0.955 to remove cross-coordinator settlement (the protocol no longer carries settlement primitives; see spec/0.955.md).
**Compiled:** 2026-05-23

A single WCP coordinator is a coordination root. Federation lets multiple coordinators interoperate so that a worker registered on Coordinator A can take a task posted to Coordinator B, and reputation accrued on either coordinator informs matching on both.

Federation is **opt-in per coordinator pair**, **trust-anchor-policy-gated**, and **rides on the same eight RPCs** as single-coordinator operation. No new RPCs are introduced.

Cross-coordinator settlement is out of scope for WCP. Marketplaces, ERPs, grant systems, or any other settlement layer that needs cross-coordinator value transfer build that layer on top using the WCP audit chain events (`task_completed`, `task_voided`, `task_aborted`) as the trusted signal of work completion across coordinators. The federation surface below provides the coordination and audit-interop substrate on which those layers are built.

## 1. Trust anchors

A federation peer relationship is established by exchanging signed trust anchors:

```json
{
  "schema_version": "wcp/0.2",
  "peer_coordinator_did": "did:wcp:<peer-coord>",
  "peer_endpoint": "wss://peer.example.org/wcp/federation",
  "trust_classes_accepted": ["capability_discovery", "reputation_query", "audit_chain_export"],
  "since": "ISO-8601",
  "expires": "ISO-8601",
  "signed_by_local_coordinator": "ed25519:..."
}
```

`trust_classes_accepted` is a closed set of:

- `capability_discovery`: peer's workers visible in this coordinator's `capabilities/subscribe` results
- `reputation_query`: this coordinator queries peer's reputation pointer for workers seen on the peer
- `audit_chain_export`: peer accepts this coordinator's audit chain entries as evidence of work completion (e.g. for a settlement layer that watches cross-coordinator `task_completed` events, or for a recheck-related audit trail)

A coordinator MAY reject any subset; mutual `trust_classes_accepted` is the effective surface.

Removed at v0.955: the `cross_coordinator_settlement` trust class. Settlement is no longer a protocol concern; cross-coordinator value transfer happens at a layer above WCP that consumes the federated audit chain.

## 2. Federation discovery

When a worker publishes a CapabilityDescriptor, the DID document `service` array MAY include:

```json
{
  "id": "#wcp-reputation-pointer",
  "type": "WcpReputationPointer",
  "serviceEndpoint": "https://coordinator-a.example.org/wcp/reputation/<worker-did>"
}
```

A querying coordinator that trusts the pointed-to coordinator MAY fetch the reputation summary. Reputation summaries are signed by the issuing coordinator with `schema_version: wcp/0.2`.

## 3. Cross-coordinator capability discovery

When an agent calls `capabilities/subscribe` on Coordinator A and `filter.federation: true`, Coordinator A MAY include workers from its federation peers in the stream, decorated with their origin:

```
Stream message:
{
  "worker_id": "did:wcp:...",
  "origin_coordinator": "did:wcp:<peer-coord>",
  "capabilities": <CapabilityDescriptor>,
  "revision": 42,
  "federation_trust_class": "capability_discovery"
}
```

Coordinator A is responsible for de-duplication. The agent MAY choose to call `tasks/post` against Coordinator A (which then forwards to the peer) or against the peer directly.

## 4. Cross-coordinator task posting

The agent posts to Coordinator A with `task.constraints.federation: true`. Coordinator A MAY forward to a peer that has an eligible worker. The forwarded post carries:

```json
{
  "task": { ... },
  "expiry": "...",
  "federation_origin": "did:wcp:<coord-a>",
  "federation_routing_sig": "ed25519:..."
}
```

The peer coordinator authenticates the federation origin and proceeds with the standard `tasks/post` flow. Settlement, where applicable, is the concern of the layer above WCP: the marketplace, ERP, or other settlement system that originated the task watches the audit chain on both coordinators (via `audit_chain_export` trust) and runs its own value-transfer logic. The protocol no longer bridges escrow across federation peers.

## 5. Audit chain interop

Federation peers expose `/wcp/audit/<task_id>` (HTTPS GET, signed JSON response) returning the audit chain entries for a federated task. The querying coordinator verifies signatures against the peer's coordinator DID. The audit chain entries (especially the terminal `task_completed`, `task_voided`, or `task_aborted`) are the canonical record of what happened on the peer; any settlement layer that needs the cross-coordinator completion signal pulls it from here.

### 5.1 Federation-layer audit-chain entry kinds

The federation layer adds the following audit-chain entry kinds. They are emitted on the LOCAL coordinator's chain and are observable through `audit/observe`:

| Entry kind | Emitted when |
|---|---|
| `federation_capability_advertised` | A peer worker becomes visible in the local subscription stream under `capability_discovery` trust class |
| `federation_task_forwarded` | A `tasks/post` call crosses the federation boundary outbound (status=accepted or rejected) |
| `federation_audit_chain_imported` | A peer audit chain segment was fetched and verified locally under `audit_chain_export` trust class |
| `federation_trust_anchor_revoked` | The operator invoked `TrustAnchorStore.remove(peer_did)`; payload carries `peer_coordinator_did`, `revoked_at`, `reason` |

Revocation is recorded as `federation_trust_anchor_revoked` on the audit chain; mid-session anchor invalidation is the operator's call. A `FederationRouter.forward_task` invocation against a peer whose anchor was revoked since the caller picked it raises `PeerTrustAnchorRevoked` rather than issuing the cross-coordinator call under a torn-down trust relationship.

## 6. Reputation portability across coordinators

A worker's reputation is **single-DID** by spec/1.0-rc1 Section 7.1. Two coordinators that federate on `reputation_query` agree to:

- Honor each other's reputation pointers (DID document `service` entries)
- Sign reputation summaries with structured fields:

```json
{
  "schema_version": "wcp/0.2",
  "worker_did": "did:wcp:...",
  "issued_by_coordinator": "did:wcp:<coord>",
  "issued_at": "ISO-8601",
  "summary": {
    "completed_tasks": 142,
    "voided_tasks": 2,
    "attestation_pass_rate": 0.96,
    "avg_time_to_complete_minutes": 38,
    "task_classes_covered": ["scheduled_presence", "observe_and_report"],
    "worker_class_modes_covered": ["human"]
  },
  "sig": "ed25519:..."
}
```

A consuming coordinator MAY weight cross-coordinator reputation against its own per-coordinator policy (e.g., 0.7x for peers in their first 12 months of federation).

## 7. Federation errors

See `error-codes.md` for the -5xxxx range:

```
-50001  FEDERATION_PEER_UNKNOWN
-50002  FEDERATION_TRUST_INSUFFICIENT
-50003  FEDERATION_PEER_UNREACHABLE
-50004  FEDERATION_REPUTATION_STALE
-50005  FEDERATION_AUDIT_VERIFICATION_FAILED
-50006  FEDERATION_JURISDICTION_REFUSED  (peer is in a non-compliant jurisdiction per local policy)
```

## 8. What federation does NOT do

- It does not centralize: there is no global directory. Federation is a bilateral relationship.
- It does not move value across coordinators. Cross-coordinator settlement is out of scope at the protocol layer; build the cross-coordinator value-transfer layer above WCP using `audit_chain_export` trust on both peers.
- It does not bypass local conformance: a federated worker MUST still satisfy the local coordinator's `attestation_requirement`. Federation does not relax verification.
- It does not enforce uniform reputation policy: each coordinator interprets cross-coordinator reputation per its own rules.

## 9. Future work tracked in RFCs

- RFC 0016 (federation primitives): this document's normative core.
- RFC 0022 (federation discovery scaling): how to discover peers without a global directory while avoiding O(N^2) bilateral negotiations.
- RFC 0023 (federation jurisdictional defaults): proposed table of jurisdiction-pair defaults (e.g., EEA cross-border under SCCs).
