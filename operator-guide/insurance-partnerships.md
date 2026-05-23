# Operator Guide: Insurance Partnerships

**Status:** RECOMMENDED practice; not normative. Specific insurer names below are examples only.

Physical-world work has tail risk: a contractor damages property, a robot injures a bystander, a payload is lost. Operators typically partner with one or more insurers to socialize this risk.

WCP's contribution: the settlement `split[]` SHOULD include a named `insurance-pool` party at a small percentage (1-5%) of every task. The pool's DID is referenced; the underlying coverage is operator-arranged.

## Common coverage classes

| Class | What it covers | Typical pricing |
|---|---|---|
| Property damage | Contractor damages customer property; robot collides with structure | 0.5-2% of task value |
| Bodily injury | Worker injures third party | 1-3% of task value, jurisdictional risk-pricing |
| Worker injury | Worker injures themselves at the task site | varies; sometimes part of workers' compensation |
| Lost or damaged payload | Transport tasks where the payload doesn't arrive intact | premium tied to declared payload value |
| Cyber liability | Audit chain breach, data exposure | operator-level rather than per-task |
| Professional indemnity | Inspection or advisory tasks where the report turns out wrong | task-class-specific |

## Partner integration patterns

### Pattern A: Single insurer, fixed percentage

The operator partners with one insurance provider. A flat percentage of every task's `settlement.amount` is routed to the insurance pool via the `split[]` entry. The insurer covers claims up to a policy cap per occurrence and per year.

Examples of insurers operators have considered in Singapore: NTUC Income, AIA Singapore, Etiqa Insurance. These are examples of one operator's choices; the protocol does not bind any insurer.

### Pattern B: Marketplace per-task insurance

The agent or the customer opts into insurance per task. The insurance percentage on `split[]` varies; the worker is told the bond reflects the chosen coverage.

### Pattern C: Worker-owned policies

The worker presents proof of their own liability policy (`required.certifications[]` includes a `liability_insurance` entry). The operator-level pool is reduced or skipped for that worker.

### Pattern D: Reinsurance for the operator pool

The operator builds an internal pool from the per-task percentages and partners with a reinsurer to cap the tail risk. The operator absorbs claims below a threshold and the reinsurer covers above it.

## Claim flow

A typical claim flow when a dispute determines that physical damage occurred:

1. Dispute resolution (per `dispute-resolution.md`) determines the damage and the attribution.
2. The operator's claims team gathers evidence from the audit chain (`spec/federation.md` Section 5 audit export).
3. The insurer's claims process kicks off via the operator-insurer integration.
4. The insurer's coverage decision is communicated to the parties.
5. An audit chain entry records the claim outcome.

The protocol's role: the audit chain provides tamper-evident evidence (signed events, attestations, timestamps). This reduces the insurer's investigative burden.

## Federation considerations

For federated tasks (`spec/federation.md`), the insurance pool typically follows the origin coordinator. The peer coordinator's local insurer policy MAY apply secondarily; cross-coverage arrangements are bilateral.

## Regulatory alignment

In Singapore, the Insurance Act and MAS guidelines apply to operator-insurer agreements; the operator's compliance team handles licensing. In the EU, IDD applies. In the US, state-by-state insurance regulation applies. The protocol does not encode these; the operator-insurer template MoU lives in operator-side legal documents (templates available on request from rentably.ai pre-v1.0 final; post-v1.0 final, the steward MAY publish reference templates).

## What WCP does NOT specify

- Which insurer to partner with.
- The coverage limits.
- The premium structure.
- The claims process beyond audit chain availability.

These are operator policy.
