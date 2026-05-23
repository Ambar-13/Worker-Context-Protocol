# Operator Guide: Fraud Detection

**Status:** RECOMMENDED practice; not normative.

WCP provides signed evidence (`acceptance_attestation`, `AttestationEvidence`, audit chain) that makes some fraud attempts trivially detectable and others much harder. This document catalogs common fraud patterns and the signals operators use to detect them.

## Common fraud patterns

### Type A: Fake completion

The worker did not actually do the task; submits forged evidence.

**Counter-signals**:

- GPS track that teleports (samples whose interpolation violates `max_speed_mps` declared in the CapabilityDescriptor).
- Photo EXIF that does not match the task's `location_scope` or `time_window`.
- Customer signature collected via a signing URL the customer never opened (telemetry on the operator's signing endpoint).
- IoT beacon proximity ping from a beacon installed in a location inconsistent with the task scope.

Mitigation: M-of-N with at least one non-sensor witness for paid tasks (spec/1.0-rc1.md Section 7 Scenario 1).

### Type B: Collusion

The customer and the worker collude. The customer signs off on fake work in exchange for a kickback.

**Counter-signals**:

- Repeated customer-worker pairings over a short window.
- Customer DIDs that sign off on suspiciously many tasks for the same worker (or worker principal).
- Geographic clustering: same building, same address, same customer phone across many tasks.

Mitigation: operator-level matching diversity; pattern detection on the audit chain; spot-check audits by an independent reviewer.

### Type C: Identity theft

An attacker compromises a worker's keypair and submits work as the worker.

**Counter-signals**:

- Sudden change in geographic operating area inconsistent with the worker's history.
- Style deviation in customer-visible communication (PWA-side text patterns).
- Device fingerprint change (operator-side telemetry).

Mitigation: secure-element-backed worker keys where possible; key rotation on suspicion; multi-factor confirmation for high-value tasks; principal DID validation.

### Type D: Bond fraud

The agent posts a task with a `bond_ref` that is not actually backed by a held escrow.

**Counter-signals**:

- Coordinator MUST verify the escrow hold before accepting `tasks/post` (the `settlement_adapter.hold(...)` call in the reference coordinator).
- Repeated `bond_ref` reuse across distinct posts.

Mitigation: escrow verification at post time; idempotency-key audit.

### Type E: Bid manipulation

An attacker monitors a coordinator's claim grace window and submits bids designed to win without genuine ability to fulfill.

**Counter-signals**:

- Bid-to-completion ratio per worker (low completion rate after winning bids).
- Bid frequency without acceptance (claim-and-abandon pattern).

Mitigation: reputation penalty for aborted-by-worker; require a minimum claim:complete ratio for high-value tasks.

### Type F: Dispute weaponization

A party opens disputes routinely to extract refunds or undermine competitors.

**Counter-signals**:

- Per-DID dispute rate.
- Dispute-loss rate.
- Cluster of disputes against a single counterparty.

Mitigation: dispute deposit; reputation penalty for repeated lost disputes.

## Telemetry the operator typically retains

Beyond the audit chain, operators typically retain (per privacy policy):

- Connection IP and device fingerprint per session.
- Click-stream on the PWA or app.
- Customer signing URL open and click times.
- WebRTC supervision session metadata (duration, audio levels, not raw video except per consent).

These supplement the audit chain in fraud detection but are NOT part of WCP normative spec.

## Cross-coordinator fraud detection

A worker barred for fraud on one coordinator MAY appear on another. Cross-coordinator reputation summaries (`spec/federation.md` Section 6) include `disputed_tasks` and dispute-loss rate, which feed into the receiving coordinator's matching policy.

Operators MAY publish a "denylist" service (an HTTPS endpoint returning a list of DIDs blocked for fraud). Federation peers MAY consume this list; it is opt-in.

## What WCP does NOT specify

- Specific fraud-detection algorithms or models.
- Thresholds for action (warn, throttle, suspend, ban).
- Cross-coordinator denylist content or governance.
- Customer-facing communication about fraud actions.

These are operator policy.
