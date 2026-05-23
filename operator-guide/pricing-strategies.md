# Operator Guide: Pricing Strategies

**Status:** RECOMMENDED practice; not normative.

WCP encodes settlement amounts in `TaskDescriptor.settlement.amount` (a string-encoded decimal) with `currency` as an ISO 4217 code. The protocol does not encode price-discovery mechanisms; those are operator policy.

## Pricing models in use

### Model A: Fixed price per task class

The operator publishes a price per descriptor_type and per task class. The agent's `tasks/post` carries the fixed amount; the worker accepts or skips.

This is the simplest model. Workable for recurring task classes (scheduled_presence aircon service: fixed quarterly fee per unit) but not for variable work.

### Model B: Per-time-unit + materials

The task is priced as `base_fee + (hours * hourly_rate) + materials`. The worker submits actuals via the `tasks/attest` evidence; the customer signs off; the settlement reconciles the actual against the prepaid bond.

### Model C: Bid-based

The agent posts the task with a maximum bond; eligible workers submit bids via `tasks/claim` with the `bid` field; lowest reasonable bid wins per the operator's matching rule. The 100 ms tie-break grace permits a small competition window (`spec/0.2.md` Section 3.4).

### Model D: Dynamic pricing

The operator computes a price per task using a model (urgency, current supply, time of day, weather, etc.) and presents it to both the agent and the worker. This is computationally a recommendation; the agent still posts a fixed amount.

### Model E: Subscription with surge

A subscriber-customer has a monthly fee covering N tasks at fixed amounts. Tasks beyond N are surge-priced.

## Multi-party split

The settlement `split[]` typically includes:

| Party | Typical share |
|---|---|
| Worker principal | 70-90% |
| Platform (operator) | 5-20% |
| Insurance pool | 1-5% |
| Sponsors (for sponsored cold-start) | 0-2% |
| Referrers | 0-3% |
| Government tax routing | varies |

The protocol does not bind any split; operators choose.

## Currency

WCP's `currency` field is ISO 4217. Operators choose currency per market. Cross-currency tasks (an agent in one currency hiring a worker priced in another) require operator-side currency conversion; the protocol does not encode conversion.

## Adjustments

### Partial completion

`partial_completion_schedule` on the TaskDescriptor enumerates milestones with `release_pct`. On `tasks/abort` with `proposed_settlement: split`, the schedule applies.

### Bonus for high quality

The settlement `split[]` MAY include a bonus party (the worker again, at a small additional percentage) conditional on attestation passing on first submission without review.

### Penalty for delay

Operators MAY adjust the worker's share downward for tasks completed past the `time_window.latest`. This is an operator policy; the protocol records the time of completion in the audit chain.

## Pricing transparency

Some operators publish their pricing models; others don't. WCP is neutral. Operators that compete on transparency typically publish:

- The split percentages.
- The matching rule (lowest bid? lowest bid above a quality floor? lowest bid weighted by reputation?).
- Surge multipliers and triggers.

## Anti-competitive concerns

In jurisdictions with platform-work regulation, operators must ensure pricing models do not constitute illegal price-fixing or worker-misclassification. Some patterns (operator unilaterally sets worker pay; workers cannot negotiate) draw regulatory attention.

WCP supports negotiated pricing via the `tasks/claim.bid` and `counter` fields; operators choose whether to enable negotiation.

## What WCP does NOT specify

- Specific prices, splits, or surge multipliers.
- Subsidy or cross-subsidy mechanisms.
- Currency conversion rates.
- Tax routing rules.

These are operator policy. The audit chain records what was actually settled, which is the protocol's contribution to pricing transparency.
