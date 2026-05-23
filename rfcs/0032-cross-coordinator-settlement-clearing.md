# RFC 0032: Cross-Coordinator Settlement Clearing

- Author(s): WCP TSC
- Status: **WITHDRAWN at v0.955.** Cross-coordinator settlement is out of scope for WCP. Settlement primitives moved out of the protocol entirely; marketplaces and other settlement layers build cross-coordinator value transfer above WCP using federated audit chain subscriptions. See `spec/0.955.md` Section 7.4. This RFC is preserved as history of the design exploration; do not implement.
- Type: standards-track (historical)
- Created: 2026-05-23
- Withdrawn: 2026-05-23 (v0.955)
- Targets: (none; withdrawn)

## Summary

Specifies how settlement clears across federation boundaries when an agent on Coordinator A posts a task funded against A's escrow, and a worker on Coordinator B (peered with A via a federation trust anchor) claims and fulfills the task. Introduces a new typed audit chain entry `federation-settlement-transfer` and recommends one of three clearing models for v1.1 implementations.

## Motivation

v0.2 settlement is intra-coordinator: the agent posts a task with `escrow_provider` and `split[]` on the same coordinator the worker is registered on. v0.2 federation (spec/federation.md) covers capability discovery and reputation portability but is silent on settlement.

Real cross-coordinator scenarios exist:

- An industrial-robotics operator with a regional AMR fleet (Coordinator B in London) accepts a task from a logistics agent (Coordinator A in Los Angeles). Funding sits with A's escrow provider; payout must reach B's worker principal.
- A research-operations coordinator (Coordinator A, US university) federates with a maritime-operations coordinator (Coordinator B, oceanographic institute) for ROV deployment tasks. Grant funds sit with A; the ROV principal is on B.
- A disaster-response coordinator (Coordinator A, national civil defense) federates with multiple municipal coordinators (Coordinator B-i) for drone scouts. Federal funds sit with A; municipal worker principals are on B-i.

Without a settlement-clearing primitive, federation works for discovery and execution but breaks at payout. Workers on B refuse to claim tasks they cannot reliably get paid for. Adoption of federation stalls.

## Design

### Three clearing models

#### Model (i): A-side capture, B-side payout, out-of-band reconciliation

A captures funds from agent. B pays worker from B's own balance. A and B reconcile in a settlement period (typically T+1 to T+30 days). No on-chain transfer event in the audit chain.

- **Pros:** simple; uses existing two-phase escrow at A; B's payout uses its existing rails.
- **Cons:** trust-shifts the reconciliation to bilateral accounting; audit chain does not reflect the cross-coordinator value flow.

#### Model (ii): A-side capture, on-chain transfer to B-side, B-side payout

A captures from agent. A emits a typed `federation-settlement-transfer` audit chain entry referencing a transfer proof (escrow-provider-specific receipt, Stripe Connect transfer ID, blockchain transaction hash, etc.). B's coordinator subscribes to the entry; payout to the worker principal proceeds against the verifiable transfer.

- **Pros:** audit chain captures the full value flow; B verifies receipt before paying; both coordinators have tamper-evident proof.
- **Cons:** requires escrow provider to support cross-account transfer with a verifiable receipt; not all providers do.

#### Model (iii): Shared escrow provider

A and B explicitly agree (in the federation trust anchor) to use the same escrow provider account. Settlement happens within the provider; both coordinators read the same split events.

- **Pros:** zero protocol changes beyond trust-anchor declaration; provider handles all clearing.
- **Cons:** strong coupling; A and B share a provider account boundary; not viable when peers prefer independent providers.

### Recommended primitive: Model (ii)

v1.1 normatively adopts Model (ii) as the federation settlement primitive. Model (i) is informational (operators MAY use it for low-value tasks without an audit-chain transfer entry; SHOULD migrate to Model (ii) for tasks above an operator-defined threshold). Model (iii) is an operator-choice optimization, declared in the trust anchor, that bypasses the on-chain transfer entry; conformance tests verify behavior, not the choice.

### New audit chain entry kind

```json
{
  "kind": "federation-settlement-transfer",
  "schema_version": "wcp/1.1",
  "task_id": "...",
  "claim_id": "...",
  "sender_coordinator_did": "did:wcp:zCoordA...",
  "receiver_coordinator_did": "did:wcp:zCoordB...",
  "amount": {
    "currency": "USD",
    "value": "1500.00"
  },
  "transfer_proof_ref": {
    "type": "stripe-connect-transfer | bank-wire-receipt | onchain-tx-hash | escrow-provider-receipt | other",
    "id": "tr_1234567890",
    "issued_at": "2026-05-23T14:30:00Z",
    "verification_endpoint": "https://provider.example.org/verify/tr_1234567890"
  },
  "previous_entry_hash": "..."
}
```

This entry MUST appear in both A's and B's audit chains, referencing the same transfer_proof_ref. Cross-coordinator audit verification (spec/federation.md Section 4) MUST detect divergence.

### Insurance pool handling across federation

When `split[]` includes an `insurance-pool` party (spec/0.2.md Section 5.3 example), the insurance-pool DID lives on one coordinator. v1.1 defines:

- If insurance-pool DID is on A: A's coordinator handles the insurance share directly; no cross-coordinator transfer needed for the insurance leg.
- If insurance-pool DID is on B: A's coordinator transfers the insurance share to B in the same `federation-settlement-transfer` entry as the worker payout, broken out as a sub-entry.
- If insurance-pool DID is on a third coordinator C (peered with both): a chain of two transfers, A->C and B->C, recorded as separate entries. [OPEN: efficient batched form]

### Dispute window semantics

A's dispute window starts at agent-side post time per spec/error-codes.md. B's dispute window for the worker-payout leg starts at the `federation-settlement-transfer` entry's `issued_at`. Time-synchronization drift between A and B (per spec/time-synchronization.md) is bounded; the dispute spec allows for at most 30 seconds of clock skew before triggering a federation time-sync warning.

If A's dispute closes the task (`disputed -> refunded`) AFTER B has paid the worker, the federation trust anchor MUST declare a recovery path:

- Option A: B holds back a fraction of payout for the duration of A's dispute window plus the time-sync drift bound. [Common in operator-to-operator settlement.]
- Option B: A and B share dispute risk via a federation-level insurance pool. [Requires Model (ii) extension; v1.2 candidate.]

## Drawbacks

- Adds one new audit entry kind, expanding the v1.1 schema surface.
- Operators must verify escrow-provider compatibility with cross-account transfers. Not all providers support this with verifiable receipts.
- Time-synchronization drift bounds become normative (not just advisory) when federation settlement clears across boundaries.

## Alternatives

- **Defer federation settlement to v2.0.** Leaves a working federation feature broken at payout time, blocking real adoption. Rejected.
- **Mandate Model (iii) (shared escrow).** Operators with independent regulatory or accounting requirements cannot adopt. Rejected.
- **Define settlement as fully out-of-band, audit chain captures only the work.** Loses the audit chain's value proposition. Rejected.

## Prior art

- Stripe Connect's transfer + payout split (https://stripe.com/docs/connect) [VERIFIED]: maps cleanly to Model (ii).
- Interledger Protocol ILP for cross-ledger payment routing [REASONED]: similar problem at a different layer.
- ACH and SWIFT message types for correspondent banking. The `federation-settlement-transfer` audit entry serves the same role at the protocol layer.

## Unresolved questions

1. **Dispute window semantics when funder and executor live on different coordinators with different time-synchronization assumptions.** Specifically: if A's NTP source and B's NTP source drift beyond the v0.2 tolerance during a dispute window, what is the canonical timeline? Recommendation: federation trust anchor declares a primary time source; both coordinators MUST sync to it for federated tasks.
2. **Insurance pool on third-party coordinator C.** Batched form vs separate entries. Operator-side experience needed before normalizing.
3. **Currency conversion across federation boundaries.** v0.2 settlement is single-currency. Cross-coordinator tasks may post in USD and pay in EUR (or another currency). Conversion source-of-truth, slippage allowance, and conversion-fee attribution are out of scope for RFC 0032; tracked as RFC 0035 candidate.
4. **Cross-coordinator dispute resolution.** Who arbitrates when A's coordinator declares dispute closed but B's coordinator's verifier reports the work as completed? Federation trust anchor MUST name the arbitration authority (could be either coordinator, a third coordinator, or an external body).

## Implementation track

v1.1 reference coordinator (`wcp_coordinator/`):
- New `audit_chain.entry_kinds["federation-settlement-transfer"]` recognized by audit chain verifier
- Federation router (`wcp_coordinator/federation/`) handles transfer-receipt verification per the trust anchor's declared provider list

v1.1 conformance test cases (proposed; see `conformance/test-suite/level3.json` after RFC 0032 acceptance):
- L3.federation.settle-clear-modeli: Model (i) reconciliation flow (informational)
- L3.federation.settle-clear-modelii: Model (ii) capture-transfer-payout happy path
- L3.federation.settle-clear-disputed: dispute opens at A after B has paid; recovery path engages
- L3.federation.settle-clear-insurance-third-coord: insurance share on third coordinator
- L3.federation.settle-time-drift-rejection: federation tasks reject when peer NTP drift exceeds tolerance
