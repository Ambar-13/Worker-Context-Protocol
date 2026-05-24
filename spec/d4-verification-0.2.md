# D4 Forcing Function Verification (v0.2)

**Companion to:** spec/0.2.md, spec/federation.md, spec/0.955.md
**Status:** verified pass for v0.2; the cross-coordinator settlement scenario in this document is **withdrawn at v0.955** (settlement is no longer a protocol concern). The base-D4 and cross-coordinator audit-interop scenarios remain valid; the RPC surface is now eight rather than nine.
**Compiled:** 2026-05-23

This document extends the v0.1 D4 verification (`spec/d4-verification.md`) with federation extension cells and confirms that the WCP RPC surface handles every cell without modification.

## Base D4 (carried forward from v0.1)

Three application-layer descriptors x two worker classes = six cells. Result: all six pass with no RPC modification. See `spec/d4-verification.md` for the full walks.

| | autonomous_robot | human |
|---|---|---|
| transport | A1 pass | A2 pass |
| scheduled_presence | B1 pass | B2 pass |
| observe_and_report | C1 pass | C2 pass |

## Federation extension cells (new at v0.2)

Federation primitives in `federation.md` ride on the same eight RPCs. We verify that the federation surface holds without new RPCs across four representative cells.

### F1: Cross-coordinator capability discovery

**Scenario.** Agent on Coordinator A subscribes with `filter.federation: true`. Coordinator A has a trust anchor with Coordinator B for `capability_discovery`. A worker on Coordinator B matches the filter.

**RPC walk:**

1. Agent calls `capabilities/subscribe` on Coordinator A with `filter.federation: true`.
2. Coordinator A responds with `{ subscription_id, stream_endpoint, ttl_seconds }`. Standard tasks/subscribe response shape, no extension.
3. Coordinator A forwards an inquiry to Coordinator B via Coordinator B's federation endpoint. Coordinator B responds with its workers' CapabilityDescriptors, decorated with `origin_coordinator` (a normal field on stream messages).
4. Stream message reaches the agent: `{ worker_id, capabilities, revision, origin_coordinator, federation_trust_class }`.

**Surface check.** No new RPC. The stream message payload carries `origin_coordinator` as a top-level optional field (additive minor change permitted by `semver-policy.md`). All existing implementations treat unknown fields as opaque. **Pass.**

### F2: Cross-coordinator task posting

**Scenario.** Agent on Coordinator A posts a task with `constraints.federation: true`. Coordinator A has no eligible worker; Coordinator B has one. Coordinator A forwards to Coordinator B; the eligible worker on Coordinator B claims.

**RPC walk:**

1. Agent calls `tasks/post` on Coordinator A. Coordinator A holds escrow and records the task. Standard `tasks/post` flow.
2. Coordinator A invokes `tasks/post` on Coordinator B via the federation endpoint with `federation_origin = did:wcp:coord-a` and `federation_routing_sig`. From Coordinator B's perspective, this is a standard `tasks/post`.
3. Worker on Coordinator B claims via `tasks/claim`. Coordinator B accepts.
4. Execute, attest, supervise proceed normally on Coordinator B.
5. `tasks/settle` on Coordinator B sends a federation settlement message back to Coordinator A. Coordinator A captures via its escrow_provider.

**Surface check.** No new RPC. Federation envelope fields are top-level optional. **Pass.**

### F3: Cross-coordinator reputation query

**Scenario.** Coordinator A's matching engine, evaluating a worker registered on Coordinator B (per cell F1), wants to factor in the worker's reputation accrued on Coordinator B.

**RPC walk:**

1. Coordinator A's matching engine reads the worker's DID document and finds the `WcpReputationPointer` service entry pointing to Coordinator B.
2. Coordinator A fetches the reputation summary via HTTPS GET to Coordinator B's `/wcp/reputation/<worker_did>` endpoint. Reputation summary is signed by Coordinator B.
3. Coordinator A applies its trust policy (e.g., 0.7x weight for newer federation peers) to the summary.
4. Matching proceeds with combined own-data + cross-coordinator reputation.

**Surface check.** No RPC at all (HTTPS GET on a well-known endpoint, separate from JSON-RPC). The reputation summary is a typed object with `schema_version: wcp/0.2`. **Pass.**

### F4: Cross-coordinator audit chain export

**Scenario.** A dispute on a federated task requires Coordinator A to verify Coordinator B's audit chain.

**RPC walk:**

1. Coordinator A's dispute resolution invokes Coordinator B's `/wcp/audit/<task_id>` endpoint over HTTPS.
2. Coordinator B returns a signed JSON array of AuditChainEntry objects. Coordinator A verifies the chain by calling its local `verify_chain` semantics against Coordinator B's coordinator DID.
3. The entries are used as evidence; no state mutation occurs in Coordinator A's audit chain (the dispute may produce its own audit entries on the local chain referencing the federated entries by `entry_id`).

**Surface check.** No new RPC. The audit export endpoint is a documented HTTPS surface, parallel to the JSON-RPC. The `AuditChainEntry` schema is unchanged. **Pass.**

## Cross-class plus federation matrix

For completeness, every base D4 cell is exercised under federation. Representative samples:

- (transport, autonomous_robot, federated): an AMR on Coordinator B accepts a transport task posted via Coordinator A. Attestation evidence (indoor_pose_track + customer_signature) is signed by the worker, posted to Coordinator B's `tasks/attest`. Settlement bridges back to A. **Pass.**
- (scheduled_presence, human, federated): a human contractor on Coordinator B accepts a scheduled_presence task posted via Coordinator A. Attestation (geofence_check_in_out + whatsapp_business_signed_link) flows through standard RPCs. Settlement bridges back. **Pass.**

## Conclusion

All base D4 cells (6) pass. All federation cells (4) pass. The v0.2 surface (unchanged from v0.1) handles federation without RPC modification. Variance is contained to:

- The opaque `descriptor_payload` (application-layer)
- The `attestation_requirement.evidence_schema` (extensible per RFC 0003)
- Optional top-level fields on stream messages and federation envelopes (additive minor changes per `semver-policy.md`)
- The `class_extension` on CapabilityDescriptor (opaque to RPC layer)

**v0.2 surface is locked.** Any future RFC that would require a tenth or eleventh RPC fails the D4 test and must redesign within the existing surface (typically by extending `evidence_schema`, `descriptor_payload`, or `class_extension`) or accept a MAJOR version bump.
