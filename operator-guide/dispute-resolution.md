# Operator Guide: Dispute Resolution

**Status:** RECOMMENDED practice; not normative.

WCP defines a `disputed` state in the settlement state machine (`spec/0.2.md` Section 1). The protocol does not define WHO resolves disputes or HOW. Those are operator policies. This document describes patterns.

## What enters dispute state

The `disputed` state is entered when:

- The verifier returns `fail` and the worker contests.
- A party opens a dispute within the `dispute_window` (default 72 hours after `settled`).
- A `tasks/abort` is submitted with `proposed_settlement: dispute`.

## Escalation ladder

A typical operator-defined ladder:

| Tier | Resolver | Time window | Cost |
|---|---|---|---|
| 0: automated | Verifier ruleset, possibly LLM-assisted review of evidence | minutes | $0 |
| 1: operator support | Operator's customer-support team reviews | 1-3 business days | operator-side cost |
| 2: panel | Operator-selected panel of 3 community reviewers (peer arbitration) | 5-10 business days | small fee |
| 3: external arbitration | Independent arbitration body (e.g., SIAC in Singapore; AAA in the US) | 30-90 days | substantial fee |
| 4: courts | Civil court in the relevant jurisdiction | months to years | substantial fee |

Operators publish their ladder publicly. Conformance does not bind operators to any specific resolver.

## Arbitrator selection

For Tier 2 (panel), patterns include:

- **Random selection** from a pool of community reviewers with established reputation. Both parties get one peremptory strike.
- **Specialty match**: panels include at least one reviewer familiar with the task class (transport, scheduled_presence, observe_and_report).
- **Geographic match**: at least one reviewer in the task's jurisdiction.

Arbitrators MUST recuse for conflicts of interest. The audit chain records the panel selection and the decision.

## Jurisdiction handling

The TaskDescriptor's `constraints.location_scope` indicates where the work happens. The operator's terms of service typically declare:

- Governing law (usually the operator's home jurisdiction).
- Forum (usually the operator's home court system or an arbitration body).
- Cross-border-specific terms when the task crosses jurisdictions (rare for physical-world tasks).

For federated tasks (`spec/federation.md`), the agent's home coordinator usually governs the dispute, but the peer coordinator's audit chain export is admissible evidence.

## Decision authorities

A dispute decision results in one of:

- `settle as posted`: the originally proposed `tasks/settle` proceeds; worker is paid in full.
- `settle partial`: a portion of the bond releases per a `partial_completion_schedule`-like split.
- `refund`: held bond returns to the agent.
- `split between parties`: customizable; recorded in the audit chain.
- `escalate`: move to the next tier.

The decision is recorded as an audit chain entry with `event_type: dispute_resolved`, carrying the resolver DID, the decision, and the rationale (free text, potentially redacted per privacy policy).

## Worker reputation impact

Operators typically adjust the worker's reputation summary based on dispute outcome:

- Worker wins: no negative impact; possibly small positive ("contested and validated").
- Worker loses: negative impact proportional to severity.
- No-fault settlement: no impact (e.g., act-of-God interruptions).

The dispute outcome is reflected in cross-coordinator reputation summaries (`spec/federation.md` Section 6).

## Customer protection

Operators typically offer a "good faith refund" path for low-value disputes where the cost of arbitration exceeds the bond amount. This is a marketplace cost; the worker is not penalized for refunds in the good-faith tier.

## What WCP does NOT specify

- The resolver identity at each tier.
- The fee structure.
- The governing law or forum.
- The reputation penalty curve.
- Whether disputes are public or confidential.

These are operator policy choices. The conformance suite verifies that the lifecycle states `disputed`, `settled`, `refunded` are reachable and that the audit chain records the transition; it does not test resolver behavior.
