# RFC 0010: RPC tasks/settle

- Author(s): Rentably
- Status: accepted (part of v0.1)
- Type: standards-track
- Created: 2026-05-23

## Summary

`tasks/settle` triggers the settlement layer (Stripe two-phase escrow by default) to release, refund, or partially release bonded funds.

## Design

See `spec/0.1.md` Section 3.7.

Request: `{ claim_id, decision: "release" | "refund" | "partial", amount, party_breakdown[] }`. Response: `{ settlement_id, state, receipt_url? }`.

`party_breakdown` is the post-split list; sum MUST equal `amount` (within rounding tolerance per RFC TBD on rounding rules).

Dispute window: 72 hours from `settled` state, any party MAY open a dispute, moving the claim to `disputed`. Funds held in delayed-release pool.

## Implementation track

`wcp_coordinator.tasks_service.settle` plus `wcp_coordinator.settlement_adapter.StripeAdapter`. Tests cover release, refund, and partial paths.
