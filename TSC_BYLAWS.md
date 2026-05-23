# WCP Technical Steering Committee Bylaws

**Companion to:** `GOVERNANCE.md`, `CHARTER.md`, `RFC_PROCESS.md`
**Status:** governance
**Compiled:** 2026-05-23

This document operationalizes the Technical Steering Committee (TSC) introduced in `CHARTER.md`.

## 1. Composition

Per `CHARTER.md`:

| Month | Min members | Worker-class representation | Org-cap |
|---|---|---|---|
| 0 (v0.1) | 1 (principal as interim chair) | seed | 1 of 1 |
| 2 | 3 | 1 academic, 1 worker provider | 2 of 3 |
| 4 (v0.5) | 5 | 1 academic, 1 robot provider, 1 human provider, 1 independent | 2 of 5 |
| 12 (v1.0 final) | 7 | as above plus 1 steward representative | 2 of 7 |

A TSC seat is held by a named individual, not a corporate seat. Two members from the same organization is the cap.

## 2. Term and rotation

- TSC seats are 2-year renewable terms.
- At least one seat opens every 12 months to prevent stasis.
- Renewal requires majority TSC vote.
- The chair role rotates annually among TSC members.

## 3. Voting

- **Quorum**: 50%+1 of seated members.
- **Simple majority**: most decisions including standards-track RFC approvals.
- **Two-thirds majority**: charter or bylaws amendments; breaking spec changes.
- **Unanimous**: amendments to `DONATION_COMMITMENT.md` or `NON_COERCION_COMMITMENT.md` pre-donation.

Votes are public; recorded in `governance-log/` with member name, vote, and date.

## 4. Conflict of interest

A TSC member MUST recuse themselves from decisions where they or their employer have direct commercial interest beyond ordinary WCP implementation. Examples requiring recusal:

- Approving a conformance certification for one's own employer's implementation.
- Deciding on a federation peer admission where the peer is one's own employer.
- Voting on an RFC sponsored by a direct competitor's product team.

Recusal is recorded in the decision log. A TSC with too many recusals on a particular vote MAY co-opt outside reviewers on a one-time basis with chair's approval.

## 5. Meetings

- **Cadence**: monthly working group calls, plus async via GitHub Issues, Discussions, and PR comments.
- **Notice**: 7 days for regular meetings; 24 hours for emergency meetings.
- **Minutes**: published within 5 business days under `governance-log/<YYYY-MM-DD>-tsc-minutes.md`.
- **Open vs closed**: meetings are open by default. Closed sessions are permitted for personnel, security disclosure, or trademark enforcement; the agenda is published in advance with closed-session items marked.

## 6. Nominations and elections

When a TSC seat opens:

1. The chair posts a call for nominations with a 30-day window.
2. Anyone may self-nominate or be nominated by another community member (with consent).
3. The TSC reviews nominations against the eligibility criteria in `CHARTER.md`.
4. A vote among current TSC members selects the new member by simple majority.
5. If no nominee receives majority, the seat remains open and a second nomination window opens.

For seats that require specific worker-class representation, the nomination call states the constraint.

## 7. Removal

A TSC member MAY be removed by two-thirds majority for:

- Sustained absence (3+ consecutive missed meetings without notice).
- Violation of `CODE_OF_CONDUCT.md` substantiated by the conduct process.
- Conflict of interest that the member refuses to acknowledge with recusal.

A removed member MAY appeal to the steward (post-donation) or to a community vote (pre-donation; details published when triggered).

## 8. Working groups

The TSC MAY charter working groups (WGs) for focused work:

- Security WG (chartered by default; reports to TSC; reviews `SECURITY.md` and `security-baseline.md` updates)
- Federation WG (chartered by default; reports on `federation.md` and RFCs 0016 and 0022-0023)
- Conformance WG (chartered by default; maintains `conformance/`)

A WG's chair reports at TSC meetings. WG decisions on their charter scope are TSC-acknowledged but not separately voted unless escalated.

## 9. External relationships

The TSC speaks for the project externally on:

- Liaison with the steward (pre-donation; donation negotiations).
- Liaison with peer standards bodies (Linux Foundation, IEEE RAS, OASIS Open, ROS-Industrial Consortium, W3C).
- Liaison with adopting vendors and operators on non-conformance-related matters.

Individual members MAY speak as themselves; statements attributed to the TSC require simple-majority approval.

## 10. Amendments

These bylaws MAY be amended by two-thirds TSC vote at a regular meeting. Proposed amendments MUST be posted as a PR against this file with 14-day discussion period before vote.

## 11. Pre-v1.0 final notes

The principal at Rentably serves as interim chair until the Month 2 transition. The interim chair does not have a casting vote; ties at single-member quorum are resolved by deferring the decision to the next meeting (where additional TSC members will have been seated).
