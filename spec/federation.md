# WCP Federation Primitives

**Companion to:** spec/1.0-rc1.md
**Status:** normative
**Compiled:** 2026-05-23

A single WCP coordinator is a marketplace operator. Federation lets multiple coordinators interoperate so that a worker registered on Coordinator A can take a task posted to Coordinator B, and reputation accrued on either coordinator informs matching on both.

Federation is **opt-in per coordinator pair**, **trust-anchor-policy-gated**, and **rides on the same nine RPCs** as single-coordinator operation. No new RPCs are introduced.

## 1. Trust anchors

A federation peer relationship is established by exchanging signed trust anchors:

```json
{
  "schema_version": "wcp/1.0-rc1",
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
- `audit_chain_export`: peer accepts this coordinator's audit chain entries as evidence in a dispute
- `cross_coordinator_settlement`: split entries in `tasks/settle` MAY reference DIDs governed by the peer

A coordinator MAY reject any subset; mutual `trust_classes_accepted` is the effective surface.

## 2. Federation discovery

When a worker publishes a CapabilityDescriptor, the DID document `service` array MAY include:

```json
{
  "id": "#wcp-reputation-pointer",
  "type": "WcpReputationPointer",
  "serviceEndpoint": "https://coordinator-a.example.org/wcp/reputation/<worker-did>"
}
```

A querying coordinator that trusts the pointed-to coordinator MAY fetch the reputation summary. Reputation summaries are signed by the issuing coordinator with `schema_version: wcp/1.0-rc1`.

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
  "bond_ref": "<opaque escrow ref on Coordinator A>",
  "expiry": "...",
  "federation_origin": "did:wcp:<coord-a>",
  "federation_routing_sig": "ed25519:..."
}
```

The peer coordinator authenticates the federation origin and proceeds with the standard `tasks/post` flow. Settlement is bridged: the bond is held by Coordinator A's escrow_provider; the peer coordinator's claim resolution drives a settlement message back to Coordinator A, which then captures.

## 5. Audit chain interop

Federation peers expose `/wcp/audit/<task_id>` (HTTPS GET, signed JSON response) returning the audit chain entries for a federated task. The querying coordinator verifies signatures against the peer's coordinator DID and may use the entries as evidence in a dispute.

## 6. Reputation portability across coordinators

A worker's reputation is **single-DID** by spec/1.0-rc1 Section 7.1. Two coordinators that federate on `reputation_query` agree to:

- Honor each other's reputation pointers (DID document `service` entries)
- Sign reputation summaries with structured fields:

```json
{
  "schema_version": "wcp/1.0-rc1",
  "worker_did": "did:wcp:...",
  "issued_by_coordinator": "did:wcp:<coord>",
  "issued_at": "ISO-8601",
  "summary": {
    "completed_tasks": 142,
    "disputed_tasks": 2,
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
- It does not require currency conversion: cross-coordinator settlements are constrained to TaskDescriptor's declared currency; the peer either supports it or rejects the federated post.
- It does not bypass local conformance: a federated worker MUST still satisfy the local coordinator's `attestation_requirement`. Federation does not relax verification.
- It does not enforce uniform reputation policy: each coordinator interprets cross-coordinator reputation per its own rules.

## 9. Future work tracked in RFCs

- RFC 0016 (federation primitives): this document's normative core.
- RFC 0022 (federation discovery scaling): how to discover peers without a global directory while avoiding O(N^2) bilateral negotiations.
- RFC 0023 (federation jurisdictional defaults): proposed table of jurisdiction-pair defaults (e.g., EEA cross-border under SCCs).
