# Failure Mode Catalog

A comprehensive list of failure modes in WCP deployments, what each looks like to the protocol, and the recovery path. Operators should review this catalog when designing the deployment's runbook.

## 1. Coordinator unreachable

### Symptom
- Worker's WebSocket connection to coordinator drops.
- Worker cannot submit attestation evidence or claim new tasks.
- Heartbeats fail.

### Severity
Medium for the coordinator's whole worker pool; high for tasks in flight.

### Behavior
- Workers with `connectivity_profile = "continuous"` (default per RFC 0029) stall after the heartbeat-miss threshold (default 3 misses); coordinator transitions any in-flight tasks to `tasks/supervise(connectivity_lost)`.
- Workers with `connectivity_profile = "intermittent"` or `"unpredictable"` (RFC 0029 preview) buffer audit entries locally. On reconnect, the buffer replays via `BufferedAuditChain.replay_on_reconnect(...)`.
- New tasks posted by agents stall in `posted` state until a worker can claim. Eligible workers cannot claim while disconnected.

### Recovery
- Coordinator recovery via standard ops (restart, DB recovery, scale-out).
- WCP-Lite workers replay buffered entries; hash chain verification ensures no in-flight evidence is lost.
- Continuous workers reconnect and resume; supervision handoff is closed if the work continued autonomously.

### What WCP does NOT do
- Failover to a backup coordinator. Coordinator HA is operator-side.
- Cross-coordinator failover. Federation peers do not automatically take over a downed coordinator's workers; trust anchors are bilateral and explicit.

## 2. Worker disappears mid-task

### Symptom
- Worker's WebSocket disconnects during execution.
- Heartbeats stop arriving at the coordinator.
- The task's `claim_id` is stuck in `executing` state.

### Severity
Variable; high for time-sensitive tasks (emergency response, healthcare logistics).

### Behavior
- Coordinator's heartbeat-miss threshold trips. The task transitions to `tasks/supervise(connectivity_lost)`.
- The supervision handoff goes to the operator's supervisor pool (or the agent, depending on the task's `supervision` config).
- If no supervision response within the supervisor-timeout, the task moves to `disputed`.
- The agent's dispute resolution invokes per the override_authority chain.

### Recovery
- Worker may rejoin and continue (resume the executing state). Coordinator MAY accept the resume if the supervision handoff is still open.
- Worker may rejoin and abort with the standard `tasks/abort` flow.
- Worker may be permanently lost (battery dead, network gone, hardware failure); the task disputes, and the agent may repost.

### What WCP does NOT do
- Automatically transfer the task to another eligible worker. Re-allocation requires operator policy and a new `tasks/post`.

## 3. Network partition between Coordinator A and B (federation)

### Symptom
- Coordinator A's federation peer (Coordinator B) is unreachable.
- Tasks federated to B do not return state updates.
- Cross-coordinator audit chain export fails.

### Severity
Medium. Affects only federated tasks; intra-coordinator tasks continue.

### Behavior
- Tasks already federated to B continue in B (workers there execute as normal).
- New tasks A would have federated stay on A.
- A's federation trust anchor's freshness policy determines what happens to in-flight federated tasks. If the trust anchor expires during the partition, A may revoke federation; B's tasks become orphaned from A's perspective.
- The `federation-settlement-transfer` audit entry (per RFC 0032) waits for B to come back online before A can capture and emit.

### Recovery
- Federation peer reconnects; tasks resume.
- Federation peer is permanently down; A's operator decides whether to:
  - Mark in-flight federated tasks as `disputed` and refund the agent
  - Wait for an explicit revocation message from B (if B comes back)
  - Apply the trust anchor's `dispute_recovery_policy` (RFC 0032 helper) to handle the value flow

### What WCP does NOT do
- Multi-coordinator quorum or consensus. Federation is bilateral, not a distributed consensus protocol.

## 4. Attestation evidence rejected

### Symptom
- Worker submits `tasks/attest` with evidence.
- Coordinator's verifier rejects (signature invalid, evidence kind unknown, M-of-N threshold unmet, time-drift exceeded, trust-class minimum unsatisfied per RFC 0033).
- Task moves to `disputed` state.

### Severity
Low for individual tasks; high if a systematic issue (operator's verifier misconfigured, worker's clock skewed).

### Behavior
- The task's `claim_id` enters `disputed`.
- Override authority (declared in the task descriptor) is notified.
- Override authority can: accept the override with manual review (signed override audit entry), reject the override (task stays disputed for operator review), or escalate.

### Recovery
- Override authority signs an override entry; task settles with the override flag recorded in the audit chain.
- Override authority rejects; agent disputes settlement; operator-side dispute resolution proceeds.

### What WCP does NOT do
- Provide a default arbitration body. Override authority is task-specified; operator-side process handles further escalation.

## 5. Settlement provider failure

### Symptom
- Coordinator attempts to capture funds via `escrow_provider`; the provider's API returns errors or is unreachable.
- The task is in `attested` state with `settle_status = pending`.

### Severity
High for monetized tasks. Coordinator MUST retry per the escrow provider's documented backoff.

### Behavior
- Task remains in `attested-but-unsettled` state.
- Worker's payout is delayed.
- Audit chain entries continue to record settlement attempts (with error codes).
- Agent's escrow hold remains in place until either capture succeeds, refund is initiated, or operator-side intervention.

### Recovery
- Escrow provider recovers; coordinator retries; capture succeeds.
- Operator-side intervention: manual capture, manual refund, or escalation to escrow provider support.
- For Model (ii) federated settlement (RFC 0032), this same logic applies to the `federation-settlement-transfer` step.

### What WCP does NOT do
- Hold money directly. WCP records the value flow; the escrow_provider holds and moves money. WCP's audit chain provides the receipts and signed evidence.

## 6. Compromised worker key

### Symptom
- Worker's signing key is suspected or known compromised (e.g., the worker device was physically tampered, the key file was leaked, the worker's TEE attestation envelope is invalidated).
- Operator detects via out-of-band signals (security incident report, audit anomaly, key-rotation policy trigger).

### Severity
High. A compromised worker can backdate tampered evidence within the worker-buffered window (RFC 0029) and present plausible-looking attestation.

### Behavior
- Operator declares the worker DID compromised via an audit chain entry (a `worker_key_compromised` event).
- Open `claim_id`s for that worker are moved to `disputed` pending forensic review.
- Future evidence signed by the compromised key is rejected.
- The worker MAY rotate to a new key under the same DID per the DID method spec; reputation history is preserved on the DID.
- RFC 0033 trust class is downgraded if the compromise affects hardware attestation.

### Recovery
- Forensic review of the audit chain entries signed by the compromised key. Hash-chain integrity gaps indicate tampering points.
- Affected tasks are settled or refunded per dispute resolution outcomes.
- Worker rotates to a new key (or new DID, depending on the operator's policy). Reputation history persists or is reset per operator policy.

### What WCP does NOT do
- Detect compromise. Detection is operator-side or via external trust root revocation (RFC 0034).
- Automatically rotate keys. Rotation is operator/worker driven.

## 7. Clock skew beyond tolerance (TIME_DRIFT_EXCEEDED)

### Symptom
- Worker submits evidence with a `submitted_at` timestamp that exceeds the coordinator's tolerance (per `spec/time-synchronization.md`).
- Coordinator emits `TIME_DRIFT_EXCEEDED` error and rejects the evidence.

### Severity
Low for individual incidents; medium if systematic (worker's clock is broken, NTP failure).

### Behavior
- Evidence is rejected with explicit drift marker in the audit chain.
- Task remains in `executing` until the worker can submit fresh evidence with a valid timestamp.
- For WCP-Lite workers (RFC 0029), the drift tolerance is wider: `min(max_offline_duration_seconds * 0.01, 30 seconds)`. Workers exceeding this MUST resync their clock on reconnect before emitting buffered entries.

### Recovery
- Worker resyncs clock (NTP, GPS, coordinator-provided time).
- Worker re-submits the evidence with corrected timestamp.

### What WCP does NOT do
- Provide a time source. The worker's time source is the worker's responsibility (NTP, GPS, the device's own RTC). WCP enforces drift bounds but does not synchronize clocks.

## 8. Coordinator audit chain corruption

### Symptom
- The audit chain's hash links no longer match (intentional tampering, database corruption, storage failure).
- Verification queries return `chain_verifies = false`.

### Severity
Critical. The audit chain's tamper-evidence is the protocol's main forensic asset.

### Behavior
- Coordinator emits a critical alert.
- All in-flight tasks freeze pending operator investigation.
- Federation peers are notified (if applicable) so they can flag federated audit chain entries that referenced corrupt entries.
- Operator-side forensic recovery: restore from backup, identify the corruption point, document for regulatory/auditor review.

### Recovery
- Restore audit chain from a verified backup (operator-side).
- Re-verify all tasks attested after the restoration point.
- If recovery is impossible: declare the affected range of tasks `void`, refund agents, document for regulatory submission.

### What WCP does NOT do
- Provide audit chain backup, replication, or HA. Audit chain durability is operator-side infrastructure.

## 9. Federation trust anchor expiry mid-task

### Symptom
- Coordinator A and B have a federation trust anchor that expires while a federated task is in flight.
- The next federation operation (capability sync, cross-coordinator audit verify, federation settlement transfer) fails.

### Severity
Medium. Affects only the federated task; the trust anchor's expiry is a known event, so this should be a configuration miss rather than a surprise.

### Behavior
- The federation operation that triggered the expiry check returns an error.
- The task continues in B (since B already accepted the claim); B's worker completes execution.
- The cross-coordinator audit chain entries cannot be exchanged until a new trust anchor is provisioned.

### Recovery
- Operators provision a renewed trust anchor (out-of-band; not via WCP).
- The federated task's audit chain entries are exchanged during the next federation sync.

### What WCP does NOT do
- Auto-renew trust anchors. Trust anchor provisioning is operator-side and security-sensitive; auto-renewal would introduce a substantial attack surface.

## 10. Worker buffer overflow (WCP-Lite)

### Symptom
- A WCP-Lite worker accumulates audit chain entries during disconnect.
- The buffer reaches its declared `buffer_capacity_audit_entries`.
- The next attempted append raises `BufferOverflowError`.

### Severity
High for the affected task; the worker MUST abort the task.

### Behavior
- The worker's preview module raises `BufferOverflowError`.
- The worker MUST emit a `task_aborted_buffer_overflow` event on reconnect (per RFC 0029).
- The task moves to `disputed`; the operator's dispute resolution proceeds.

### Recovery
- Operator provisions a larger buffer in the worker's `class_extension`.
- Operator-side review: was the disconnect window longer than expected? Was the per-task entry rate higher than expected?
- The task may be reposted to a different worker (or the same worker with the new buffer config).

### What WCP does NOT do
- Auto-resize buffers. Buffer capacity is a worker capability declaration; it does not change at runtime.

## Cross-cutting principles

1. **WCP is not the safety system.** Many failure modes above describe network and operational failures. None of them are safety hazards on their own; the safety system is independently certified and unaffected by WCP failures. See `docs/limits/safety-system-boundary.md`.

2. **The audit chain is the forensic record.** Even when things fail, the audit chain should record what happened, when, and who reported it. Operators rely on the chain for incident review.

3. **Dispute is the universal escape hatch.** When verifier semantics, trust assumptions, or settlement guarantees break, the task transitions to `disputed`. The operator's dispute resolution policy handles the rest.

4. **Operator-side runbooks matter.** WCP gives operators primitives; the runbook for "what to do when X fails" is operator-side and deployment-specific.

## See also

- `docs/limits/wcp-is-not.md` for the canonical non-use list
- `docs/limits/real-time-boundary.md` for the orchestration/control split
- `docs/limits/safety-system-boundary.md` for the safety-rated systems boundary
- `docs/limits/swarm-boundary.md` for the 1-task-1-worker assumption
- `spec/threat-model.md` for the security threat catalog (overlaps with this document but with attacker-mindset framing)
