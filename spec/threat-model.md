# WCP Threat Model

**Companion to:** spec/1.0-rc1.md
**Status:** normative
**Compiled:** 2026-05-23

This document applies STRIDE analysis (Spoofing, Tampering, Repudiation, Information disclosure, Denial of service, Elevation of privilege) per asset and per trust boundary across three adversary profiles.

## 1. Assets

| Asset | Description | Owner |
|---|---|---|
| Worker DID and keypair | Identity rooted in the worker's hardware or software keypair | Worker |
| Principal DID | Employer, owner, or operator-of-record account credential | Principal |
| Agent DID | AI-platform issued credential | Agent |
| TaskDescriptor | Posted task with bonded escrow reference | Agent |
| acceptance_attestation | Worker's signed claim acceptance | Worker |
| AttestationEvidence | Per-mode, per-kind signed proof of work | Worker |
| AuditChainEntry | Hash-linked signed event in the coordinator's log | Coordinator |
| Bonded escrow funds | Held by escrow_provider; released by tasks/settle | Settlement layer |
| Reputation pointer (DID document service entry) | Cross-coordinator reputation reference | Worker / coordinator pair |
| Capability descriptor | Worker self-published; matching input | Worker |

## 2. Trust boundaries

```
+---------+    1. signed RPC    +-------------+    2. settle      +-------------------+
| Worker  |-------------------->| Coordinator |------------------>| Escrow provider   |
| device  |                     |   (server)  |                   |  (third party)    |
+---------+                     +------+------+                   +-------------------+
                                       |
                                       | 3. signed RPC
                                       |
+---------+                       +----v----+                     +-----------+
| Agent   |---------------------->| Backend |<--------------------| Federation |
| (AI     |    4. signed RPC      | services|   5. federation     | peer       |
|  agent) |                       +---------+                     +-----------+
+---------+
```

Boundaries 1, 3, 4: signed JSON-RPC over WSS. Boundary 2: HTTPS to the escrow provider's REST API. Boundary 5: signed coordinator-to-coordinator messages per `federation.md`.

## 3. Adversary profiles

- **Rational economic adversary.** Maximizes utility; will collude if cost of collusion < expected reward. Examples: a worker who fakes completion to capture escrow; a customer who refuses sign-off to capture refund; a coordinator that biases matching toward affiliated workers.
- **Regulatory adversary.** Demands tamper-evident audit trail under PDPA, GDPR, CCPA, MOM-equivalent labor law, or jurisdictional consumer-protection regulation. Threat is exposure or invalidation of the operator's compliance posture.
- **Safety-critical adversary.** A worker may injure a human or damage property. Threat is failure mode where the protocol mechanically permits an unsafe action.

## 4. STRIDE analysis per RPC

### 4.1 capabilities/list (worker -> coordinator)

| Threat | Description | Mitigation |
|---|---|---|
| Spoofing | Adversary publishes capability under another worker's DID | Signature over canonical-JSON; coordinator MUST verify via did:wcp resolution |
| Tampering | Adversary modifies an in-flight capability descriptor | TLS 1.3 + WSS; canonical-JSON signature on the wire |
| Repudiation | Worker denies a previously published capability | Audit chain entry on every capabilities/list with signed payload_hash |
| Information disclosure | Attacker enumerates worker fleet | Coordinator MAY require agent authentication for capabilities/subscribe; rate limit |
| Denial of service | Flood of capability updates | Per-worker rate limit; revision floor; ttl_seconds-based caching |
| Elevation | None directly; capability publication is by definition self-asserting | Audit chain + verifier semantics check class_extension claims against certifications |

### 4.2 capabilities/subscribe (agent -> coordinator)

| Threat | Description | Mitigation |
|---|---|---|
| Spoofing | Attacker subscribes as another agent | Signed `agent_did`; coordinator authenticates the agent on subscribe |
| Tampering | Attacker tampers with stream | TLS 1.3 + WSS |
| Repudiation | Coordinator denies a delivered update | All stream messages signed by the coordinator's audit signer |
| Information disclosure | Subscriber discovers workers outside their authorized scope | Coordinator-side authorization on filter |
| Denial of service | Excessive subscriptions per agent | Per-agent subscription cap; ttl_seconds enforcement |
| Elevation | Subscriber attempts to mutate state via subscribe | Subscribe is read-only by spec contract |

### 4.3 tasks/post

| Threat | Description | Mitigation |
|---|---|---|
| Spoofing | Adversary posts as another agent | Signature verification |
| Tampering | Adversary modifies a task after posting | TaskDescriptor is signed by the agent; coordinator records `task_json` immutably; audit chain entry |
| Repudiation | Agent denies posting | Audit chain + signed payload |
| Information disclosure | Task details (location, payload, customer identity) leak | Privacy architecture defines PII tagging; coordinators MUST honor the worker_class_filter and not broadcast sensitive descriptor_payload beyond eligible workers |
| Denial of service | Task posting flood | Per-agent rate limit; bond requirement (held escrow) tied to task posting |
| Elevation | Agent attempts to post tasks tagged for out-of-scope classes | Reference coordinator refuses; RFC clearance gate |

### 4.4 tasks/claim

| Threat | Description | Mitigation |
|---|---|---|
| Spoofing | Adversary claims a task under another worker's DID | acceptance_attestation signature MUST be verified before state mutation |
| Tampering | Adversary modifies claim terms after acceptance | acceptance_attestation includes payload_hash binding to canonical claim payload |
| Repudiation | Worker denies acceptance | acceptance_attestation is the signed non-repudiation primitive |
| Information disclosure | Bid leak across competing workers | Coordinator MUST NOT echo competing bids to other workers within the grace window |
| Denial of service | Worker claims tasks they cannot fulfill, blocking real workers | Coordinator MAY require stake / bond on the worker side; reputation penalty on aborted-by-worker |
| Elevation | Self-dealing: posted_by == worker.principal_id | tasks/claim rejects unless attestation_requirement includes third-party-witness |

### 4.5 tasks/execute

| Threat | Description | Mitigation |
|---|---|---|
| Spoofing | Attacker emits events under a worker's DID | Each event signed; worker key bound at lifecycle activation |
| Tampering | In-flight event modified | TLS + signed events |
| Repudiation | Worker denies emitting events | Audit chain |
| Information disclosure | Event payload exposes sensitive telemetry | Operators MAY redact via privacy_architecture tombstone pattern; raw bytes never leave the worker for sensor evidence (only hashes) |
| Denial of service | Worker emits flood of events | Per-claim event rate limit |
| Elevation | Worker emits supervision_tier_changed to escape attestation | Spec section 3.8: the agent's contract does not move under the worker's feet |

### 4.6 tasks/attest

| Threat | Description | Mitigation |
|---|---|---|
| Spoofing | Attacker submits fabricated evidence | Per-evidence signature verification |
| Tampering | Evidence payload modified post-collection | payload_hash binds payload; signature over canonical-JSON |
| Repudiation | Worker denies evidence after dispute | Audit chain entry on each attestation submission |
| Information disclosure | Customer signature image leaks | Only hash leaves the worker device; raw image stays under operator's PDPA-compatible retention |
| Denial of service | Attestation submission flood | Per-claim attestation count cap |
| Elevation | Self-validating attestation (GNoME failure mode) | M-of-N requirement with at least one non-sensor witness for paid tasks; verifier discriminates by (mode, kind) not by worker class |

### 4.7 tasks/settle

| Threat | Description | Mitigation |
|---|---|---|
| Spoofing | Attacker triggers settlement under coordinator authority | tasks/settle is coordinator-internal; signed by coordinator's settlement key; escrow provider authenticates |
| Tampering | party_breakdown mutated | Audit chain entry over settle payload |
| Repudiation | Coordinator denies a settlement | Audit chain + escrow receipt |
| Information disclosure | Party identity in split exposed | Split entries are DIDs, not personal info; resolve via did:wcp method spec |
| Denial of service | Settlement provider unavailable | retry-idempotency.md defines idempotent retry; SETTLEMENT_FAILED with `retryable: true` |
| Elevation | Coordinator captures more than verifier authorized | Settlement amount derived strictly from attesting transition |

### 4.8 tasks/supervise

| Threat | Description | Mitigation |
|---|---|---|
| Spoofing | Attacker posing as supervisor | Supervisor DID authenticated; takeover_authority recorded |
| Tampering | Supervisor session video stream modified | Out-of-spec; WebRTC layer security |
| Repudiation | Supervisor denies authority | Audit chain entry with supervisor_id and takeover_authority |
| Information disclosure | Supervisor sees worker context they shouldn't | Operator-level access control |
| Denial of service | Supervision request flood | Per-coordinator pool cap; urgency-based queueing |
| Elevation | Supervisor mutates attestation_requirement | Forbidden; the agent's contract does not move |

### 4.9 tasks/abort

| Threat | Description | Mitigation |
|---|---|---|
| Spoofing | Attacker aborts another party's claim | Caller DID authenticated; abort authorization checked (worker, agent, principal, supervisor) |
| Tampering | proposed_settlement mutated | Signed payload; audit chain |
| Repudiation | Initiator denies abort | Audit chain |
| Information disclosure | state_snapshot exposes sensitive context | Privacy tombstone pattern |
| Denial of service | Repeated aborts | Per-DID rate limit; reputation penalty |
| Elevation | Worker aborts to escape attestation in the moment of failure | partial_completion_schedule applies; settlement disposition recorded |

## 5. Cross-cutting threats

### 5.1 Audit chain tampering

The audit chain is hash-linked and signed. An attacker with database access who modifies a payload without updating `payload_hash` is detected by the verify_chain check. An attacker who updates both must also forge the coordinator's signing key, which requires key compromise (out of scope for the protocol; mitigated by HSM-backed coordinator keys in production).

### 5.2 Time-source manipulation

Adversary skews timestamps to evade heartbeat timeouts or dispute windows. See `time-synchronization.md`: coordinators MUST declare a canonical time source and clients MUST surface drift > 5 seconds as a warning. Audit chain timestamps come from the coordinator, not the worker.

### 5.3 Federation poisoning

A malicious peer coordinator advertises forged worker reputation. See `federation.md`: federation trust anchors are explicit; reputation across coordinators is opt-in and weighted by trust-anchor policy.

### 5.4 Resource exhaustion

Per-DID rate limits on every RPC; per-agent subscription caps; per-claim event caps; per-coordinator memory ceiling for in-flight claims. Backpressure on WebSocket per `security-baseline.md`.

## 6. Out-of-scope

Physical tampering with the worker's hardware secure element is out of WCP's threat model. So is jurisdictional law-enforcement intervention. Operators MUST address these in their compliance posture.
