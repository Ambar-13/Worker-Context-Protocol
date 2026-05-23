# Worker Context Protocol: RFC Process

The RFC (Request for Comments) process is how the WCP specification evolves. Anyone may submit an RFC. RFCs are reviewed on a 14-day lazy-consensus cycle with Technical Steering Committee (TSC) escalation for substantive objections or breaking changes.

## Repository structure

```
rfcs/
  0000-template.md           # template for new RFCs
  0001-initial-spec.md       # initial v0.1 spec frames as RFC 0001
  0002-subcontracting-v0.2.md # tracking stub for Scenario 13
  0003-evidence-kinds-registry.md # the schema registry for AttestationEvidence kinds
  0004-rpc-capabilities-list.md
  0005-rpc-capabilities-subscribe.md
  0006-rpc-tasks-post.md
  0007-rpc-tasks-claim.md
  0008-rpc-tasks-execute.md
  0009-rpc-tasks-attest.md
  0010-rpc-tasks-settle.md
  0011-rpc-tasks-supervise.md
  0012-rpc-tasks-abort.md
  <NNNN>-<short-name>.md     # new RFCs
  <NNNN>-decision.md         # decision record after merge or rejection
```

## Submitting an RFC

1. Copy `rfcs/0000-template.md` to `rfcs/NNNN-short-name.md`, where NNNN is the next free integer.
2. Fill in required fields: summary, motivation, design, drawbacks, alternatives, prior art, unresolved questions.
3. Open a PR against `main`.
4. The PR is the discussion venue; comments and reviews accumulate.
5. If a TSC member or three or more community members raise substantive objections within 14 days, the RFC enters TSC review.

## Decision rules

- **Lazy consensus.** After 14 days open with no substantive objection, a TSC member merges the PR.
- **TSC review.** If escalated, the TSC has 21 days to decide. Decision is by simple majority quorum. Outcomes: accept, accept-with-revision, reject, defer.
- **Emergency flag.** A security or production-correctness emergency may bypass the 14-day window. Requires explicit TSC sign-off and a post-hoc public note within 7 days.

After merge, the corresponding `NNNN-decision.md` file is added recording the discussion link, the decision rationale, the date, and any required follow-up.

## Substantive objections

A substantive objection is one that:

- Names a specific technical flaw with a reproducible failure case, or
- Names a specific governance or non-coercion concern with reference to [CHARTER.md](./CHARTER.md) or [NON_COERCION_COMMITMENT.md](./NON_COERCION_COMMITMENT.md), or
- Names a prior-art conflict with a citation, or
- Names a security or privacy concern with a threat model.

"I don't like this" without a specific technical, governance, or prior-art ground is not substantive. The TSC may rule on substantivity if disputed.

## Categories

- **Standards-track**: changes to `spec/0.1.md` or `spec/schemas/*.json`. Require TSC majority. May require version bump.
- **Informational**: clarifications, examples, prior art. Lazy consensus.
- **Experimental**: new evidence kinds, new descriptor types, x-* extensions. Lazy consensus to add to RFC 0003 schema registry; promotion to standards-track requires TSC vote.

## RFC lifecycle states

```
draft -> open -> {merged | rejected | deferred | superseded}
```

- `draft` (pre-PR): author iterates locally.
- `open` (PR open): community discusses; 14-day clock running.
- `merged`: PR merged; spec extended.
- `rejected`: TSC declined.
- `deferred`: TSC parked for a future version (e.g., RFC 0002 deferred to v0.2).
- `superseded`: a later RFC replaced this one; cross-link required.

## Authorship and credit

Every RFC has a named author. Co-authors are welcome. Author roles do not grant decision authority; merge is by TSC member only.

## Implementation track

A "shipped" RFC has at least one production WCP-conformant implementation passing the conformance test suite. The shipped flag is added to the decision record.
