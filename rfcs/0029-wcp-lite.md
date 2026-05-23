# RFC 0029: WCP-Lite for Intermittent Connectivity

- Author(s): WCP TSC
- Status: open (v1.1 candidate)
- Type: standards-track
- Created: 2026-05-23 (expanded 2026-05-23 from v1.0-rc1 stub)
- Targets: v1.1

## Summary

WCP-Lite is the connectivity profile for workers that operate under predictable or unpredictable disconnection: subsea ROVs, basement-tunnel AMRs, deployed quadruped robots inside metal-clad sites, remote-field-research stations, agricultural drones beyond cellular coverage, disaster-response teams in damaged-infrastructure zones, satellite-uplinked maritime workers, mining vehicles below ground, and orbital robots on the far side of a body. WCP-Lite is NOT a protocol subset; it is a connectivity profile declared in the CapabilityDescriptor. WCP-Lite workers remain full v1.0-rc1 conformance Level 1; the spec accommodates them through a buffer-and-replay pattern with hash-chain integrity preservation across the disconnect window.

## Motivation

v1.0-rc1 (spec/1.0-rc1.md Section 7) defines a 15-second heartbeat with three-missed-beat transition to a `tasks/supervise(connectivity_lost)` flow. The spec assumes the supervisor can step in and resume control. In practice, two cases break:

1. **Predictable disconnect.** A subsea ROV at 200 meters depth has no acoustic-modem coverage for the active-tool segment of its task. It executes for 40 minutes, then surfaces and uplinks. There is no human supervisor on the surface qualified to take over mid-task; the worker is autonomous by design. Triggering `tasks/supervise` every time the ROV submerges produces a flood of false supervision requests.

2. **Unpredictable disconnect.** A disaster-response team's deployed quadruped robot enters a collapsed structure with random metal-shielding. Connectivity drops in and out unpredictably. Each drop triggers a supervision event; the operator's ops center is flooded with alerts that resolve themselves seconds later.

Both cases share the same structural property: the worker is autonomous within the disconnect window, the disconnect window is bounded, and the audit chain integrity guarantee continues to hold across the window because the worker buffers its signed entries locally and emits them in order on reconnect.

A subset spec (a smaller protocol with fewer guarantees) would be the wrong move; it fragments the ecosystem and creates two classes of workers. The right move is a connectivity profile declared on the CapabilityDescriptor that the verifier and coordinator MUST honor, with the full RPC surface unchanged.

## Design

### Capability declaration

A WCP-Lite worker declares its connectivity profile in `CapabilityDescriptor.class_extension`:

```json
{
  "class_extension": {
    "connectivity_profile": "intermittent",
    "max_offline_duration_seconds": 7200,
    "expected_disconnect_pattern": "predictable|unpredictable",
    "buffer_capacity_audit_entries": 10000
  }
}
```

- `connectivity_profile`: one of `continuous` (default; current v1.0-rc1 behavior), `intermittent` (WCP-Lite), or `unpredictable` (intermittent with no advance notice on disconnect timing).
- `max_offline_duration_seconds`: the longest disconnect window the worker can survive without losing audit chain integrity. Coordinator REJECTS tasks whose execution window plus heartbeat tolerance would exceed this value.
- `expected_disconnect_pattern`: informational hint to the matching engine. `predictable` workers can be matched against tasks whose timing aligns with their connectivity (e.g., schedule the subsea ROV's task during its planned submersion). `unpredictable` workers should be matched against tasks that tolerate arbitrary disconnect.
- `buffer_capacity_audit_entries`: how many audit chain entries the worker can buffer offline. Exceeding this is a hard error; the worker MUST abort the current task and emit a `task_aborted_buffer_overflow` event on reconnect.

### Coordinator behavior

When `connectivity_profile != "continuous"`:

1. Coordinator pauses the 15-second heartbeat enforcement during the declared `max_offline_duration_seconds` window.
2. Coordinator accepts out-of-order arrivals provided hash-chain integrity holds (entry N+1's `previous_entry_hash` matches entry N's hash).
3. Coordinator computes the dispute window starting from the timestamp when entries were RECEIVED by the coordinator, NOT when the underlying action occurred (modulo the time-synchronization spec's drift tolerance).
4. Coordinator MUST verify the hash chain across the batch on reconnect, not just the latest entry.

### Tasks/post flow

Agents posting tasks intended for intermittent workers MUST set the new optional field `accepts_intermittent_executor: true`:

```json
{
  "constraints": {
    "accepts_intermittent_executor": true,
    "max_acceptable_offline_seconds": 3600
  }
}
```

- `accepts_intermittent_executor`: explicitly opt in. Default false maintains v1.0-rc1 behavior (only continuous workers can claim).
- `max_acceptable_offline_seconds`: agent's maximum tolerance. The matching engine REJECTS workers whose declared `max_offline_duration_seconds` exceeds this.

### Worker-side audit chain buffer

A WCP-Lite worker maintains a local, signed, append-only buffer of audit chain entries during the disconnect window. The buffer is a sequence of entries with the standard WCP `previous_entry_hash` linking. On reconnect, the worker emits the buffer to the coordinator in order via standard `tasks/attest` and `audit/append` RPCs (no new RPCs needed); the coordinator's standard hash-chain verifier validates the batch.

If the worker is compromised during the offline window, the standard hash-chain forensics apply: the coordinator can identify the entry where the chain breaks (e.g., a hash collision, a backdated entry that doesn't match the next entry's `previous_entry_hash`). The coordinator MUST treat any chain break as evidence of tampering, mark the affected task as `disputed`, and trigger the standard dispute resolution flow.

### Dispute window with reconnect-delayed entries

When entries arrive late (worker reconnected after a 2-hour subsea segment), the dispute window for downstream actions (capture, settle, payout) starts when entries were RECEIVED, not when the underlying action occurred. This matters because:

- If A receives a worker's attestation entry at time T+2h, and the spec's 72-hour dispute window starts at T+2h, dispute closes at T+2h+72h.
- Agents and operators MUST understand that intermittent workers introduce additional dispute latency.
- Auditors examining the audit chain can distinguish original timestamp from received timestamp via the standard entry's `submitted_at` (worker-claimed) vs `received_at` (coordinator-stamped) fields.

### Time-synchronization

The worker's local clock drifts during offline windows. v1.0-rc1 (spec/time-synchronization.md) defines a drift tolerance for normal operation. For WCP-Lite workers, the spec accepts wider drift IF the buffered entries' hash chain is intact: drift bounded by `min(max_offline_duration_seconds * 0.01, 30 seconds)`. Workers exceeding this MUST resync their clock on reconnect via NTP or coordinator-provided time before emitting buffered entries.

### Cross-federation considerations

When a WCP-Lite worker on Coordinator B is discovered by an agent on Coordinator A via federation:

- A MUST honor B's `connectivity_profile` declaration.
- A's tasks/post intended for B's WCP-Lite worker MUST include `accepts_intermittent_executor: true`.
- Cross-coordinator settlement (RFC 0032) MUST account for the reconnect-delayed entry arrival; A's dispute window for the federation settlement transfer accommodates B's worker's `max_offline_duration_seconds`.

## Drawbacks

- Operator coordination cost: agents must know which workers are intermittent and post tasks with the right flags. Mitigation: capabilities/subscribe surface declares the profile, agents filter accordingly.
- Dispute latency growth: agents accepting intermittent workers must accept up to `max_offline_duration_seconds + 72h` total resolution latency. Acceptable for the use cases that need WCP-Lite; unacceptable for time-critical dispatch.
- Buffer-overflow class of failures: workers running tasks longer than their buffer can accommodate fail with `task_aborted_buffer_overflow`. Operators must provision buffer capacity for their worst-case disconnect.
- Forensic complexity: hash-chain forensics on a 10,000-entry buffer batch is slower than on a single entry. v1.1 reference verifier MUST handle the batch case efficiently.

## Alternatives

1. **Subset spec with reduced RPC surface.** Rejected; fragments the ecosystem and creates two classes of workers.
2. **Synchronous-only protocol; require workers to bridge disconnects via gateways.** Forces every intermittent worker to deploy a gateway, which is impractical for autonomous subsea robots and disaster-response field teams. Rejected.
3. **Use `tasks/supervise(connectivity_lost)` for every disconnect.** Floods the supervisor with false alerts for workers that are autonomous by design. Rejected.

## Prior art

- DTN (Delay-Tolerant Networking, RFC 4838) handles intermittent connectivity at the network layer. WCP-Lite operates at the application layer, building on the assumption that the underlying transport eventually delivers messages in order. [VERIFIED]
- AMQP "store-and-forward" semantics: similar buffer-and-replay pattern at the messaging layer. [VERIFIED]
- ZigBee's sleeping-end-device pattern: predictable disconnect with buffered message delivery on the parent router. The capability declaration in WCP-Lite is analogous.
- DDS (Data Distribution Service, OMG) supports persistent durability; the audit chain buffer in WCP-Lite is analogous but stronger because of cryptographic integrity.

## Unresolved questions

1. **Should `connectivity_profile` be a first-class CapabilityDescriptor field rather than a `class_extension` field?** Recommendation: yes in v1.1, given the cross-cutting impact. Migrates v1.0-rc1 implementations that placed it in class_extension via a one-time canonicalization pass.

2. **What is the right default `max_offline_duration_seconds` per worker class?** Recommendation: do not default; require the worker to declare explicitly. A missing declaration with `connectivity_profile != "continuous"` is a malformed capability, rejected by the verifier.

3. **How does WCP-Lite interact with the supervision handoff path?** When a WCP-Lite worker enters its disconnect window, should the coordinator's supervisor be informed? Recommendation: yes for `unpredictable` workers; the supervisor is told the worker is offline and given an estimated reconnect window if available. For `predictable` workers with an expected reconnect time, no notification needed.

4. **Should buffered entries support compression?** Subsea acoustic uplinks are bandwidth-constrained; a 2-hour batch of audit entries can be substantial. Recommendation: yes via a standard codec (CBOR with optional gzip), declared in capability_extension. v1.2 RFC.

5. **Replay attack window for buffered entries.** A compromised worker that buffers entries for 2 hours has a 2-hour window to forge them coherently. Forensic detection of this is harder than for online tampering. Recommendation: pair with RFC 0033 (Attestation Key Trust Classes) and require `hardware-attested-*` trust class for high-value WCP-Lite tasks.

## Implementation track

v1.1 reference coordinator (`wcp_coordinator/`):
- `wcp_coordinator/connectivity_profile.py`: handles capability declaration parsing, dispute-window adjustment, batch hash-chain verification
- Update `tasks_service.py` to handle `accepts_intermittent_executor` constraint
- Update `audit_chain.py` to verify batch arrivals

v1.1 reference field-research worker example:
- New `examples/agents/field-research/wcp_lite_worker.py` showing the buffer-and-replay pattern (does not ship in this RFC's reference; tracked as a v1.1 implementation deliverable)
- README walkthrough: a researcher deploys to a remote sensor station, executes a 4-hour observation task offline, reconnects via satellite uplink, emits the buffer batch

v1.1 conformance test cases (proposed; see `conformance/test-suite/level1.json` after RFC 0029 acceptance):
- L1.connectivity_profile.continuous_default: capability without profile field treated as continuous
- L1.connectivity_profile.intermittent_with_max_offline: capability with `intermittent` and `max_offline_duration_seconds`
- L1.batch_arrival.hash_chain_intact: buffered batch accepted when hash chain holds
- L1.batch_arrival.hash_chain_break: buffered batch rejected when an entry's previous_entry_hash mismatches
- L1.dispute_window.reconnect_delayed: dispute window starts at received_at for late-arriving entries
- L1.matching.intermittent_rejected_without_opt_in: agent's task without `accepts_intermittent_executor: true` does NOT match intermittent workers
- L1.matching.max_acceptable_offline_filter: agent's `max_acceptable_offline_seconds` filters workers correctly
- L1.buffer_overflow.task_aborted: worker exceeding buffer capacity emits `task_aborted_buffer_overflow` on reconnect
