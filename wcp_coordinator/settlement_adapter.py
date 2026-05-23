"""
Settlement adapter wrapping Stripe two-phase escrow.

INTEGRATION-GAP: the exact module name and import path of the existing
Rentably Stripe two-phase escrow flow are not provided. This adapter
defines the SettlementAdapter protocol and ships a working in-memory
fake (FakeStripeAdapter) for tests plus a thin Stripe-API shell
(StripeAdapter) that the principal can wire to the Rentably-internal
flow by replacing two method bodies.

Two-phase escrow shape (per spec/0.1.md):
  tasks/post   -> create PaymentIntent with capture_method=manual (HOLD)
  tasks/settle -> payment_intents.capture (CAPTURE) or refund (REFUND)
  tasks/abort  -> cancel or refund per disposition
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SettlementOutcome:
    settlement_id: str
    state: str  # "captured" | "refunded" | "partial" | "cancelled" | "held"
    receipt_url: str | None = None


class SettlementAdapter(Protocol):
    def hold(self, *, amount: str, currency: str, bond_ref: str) -> SettlementOutcome:
        ...

    def capture(
        self, *, bond_ref: str, amount: str, party_breakdown: list[dict]
    ) -> SettlementOutcome:
        ...

    def refund(self, *, bond_ref: str, amount: str | None = None) -> SettlementOutcome:
        ...

    def cancel(self, *, bond_ref: str) -> SettlementOutcome:
        ...


class FakeStripeAdapter:
    """In-memory fake. For tests and dev. State stored on the instance."""

    def __init__(self) -> None:
        self._intents: dict[str, dict] = {}

    def hold(self, *, amount: str, currency: str, bond_ref: str) -> SettlementOutcome:
        if bond_ref in self._intents:
            return SettlementOutcome(
                settlement_id=self._intents[bond_ref]["settlement_id"],
                state="held",
            )
        sid = "test_" + uuid.uuid4().hex[:12]
        self._intents[bond_ref] = {
            "settlement_id": sid,
            "amount": amount,
            "currency": currency,
            "state": "held",
        }
        return SettlementOutcome(settlement_id=sid, state="held")

    def capture(
        self, *, bond_ref: str, amount: str, party_breakdown: list[dict]
    ) -> SettlementOutcome:
        intent = self._intents.get(bond_ref)
        if intent is None:
            raise KeyError(f"no intent for bond_ref={bond_ref}")
        intent["state"] = "captured"
        intent["party_breakdown"] = party_breakdown
        return SettlementOutcome(
            settlement_id=intent["settlement_id"],
            state="captured",
            receipt_url=f"https://test/receipt/{intent['settlement_id']}",
        )

    def refund(
        self, *, bond_ref: str, amount: str | None = None
    ) -> SettlementOutcome:
        intent = self._intents.get(bond_ref)
        if intent is None:
            raise KeyError(f"no intent for bond_ref={bond_ref}")
        intent["state"] = "refunded"
        return SettlementOutcome(
            settlement_id=intent["settlement_id"], state="refunded"
        )

    def cancel(self, *, bond_ref: str) -> SettlementOutcome:
        intent = self._intents.get(bond_ref)
        if intent is None:
            raise KeyError(f"no intent for bond_ref={bond_ref}")
        intent["state"] = "cancelled"
        return SettlementOutcome(
            settlement_id=intent["settlement_id"], state="cancelled"
        )


class StripeAdapter:
    """Thin Stripe-API shell.

    INTEGRATION-GAP: the bond_ref returned by tasks/post is expected to be a
    Stripe PaymentIntent ID (e.g., "pi_..."). Replace the two method bodies
    below with calls into the existing Rentably stripe wrapper.
    """

    def __init__(self, stripe_client) -> None:  # type: ignore[no-untyped-def]
        self._stripe = stripe_client

    def hold(self, *, amount: str, currency: str, bond_ref: str) -> SettlementOutcome:
        # INTEGRATION-GAP: existing Rentably flow already creates the
        # PaymentIntent at task posting time, so the bond_ref is already
        # held. Confirm here instead of re-creating.
        intent = self._stripe.PaymentIntent.retrieve(bond_ref)
        if intent.status not in ("requires_capture", "requires_confirmation"):
            raise RuntimeError(
                f"PaymentIntent {bond_ref} is in state {intent.status}; "
                f"expected requires_capture"
            )
        return SettlementOutcome(settlement_id=bond_ref, state="held")

    def capture(
        self, *, bond_ref: str, amount: str, party_breakdown: list[dict]
    ) -> SettlementOutcome:
        # INTEGRATION-GAP: Stripe Connect transfers per party_breakdown are
        # set up against the Rentably internal payouts pipeline.
        intent = self._stripe.PaymentIntent.capture(
            bond_ref, amount_to_capture=int(float(amount) * 100)
        )
        return SettlementOutcome(
            settlement_id=intent.id,
            state="captured",
            receipt_url=intent.charges.data[0].receipt_url
            if intent.charges and intent.charges.data
            else None,
        )

    def refund(
        self, *, bond_ref: str, amount: str | None = None
    ) -> SettlementOutcome:
        refund_kwargs = {"payment_intent": bond_ref}
        if amount is not None:
            refund_kwargs["amount"] = int(float(amount) * 100)
        self._stripe.Refund.create(**refund_kwargs)
        return SettlementOutcome(settlement_id=bond_ref, state="refunded")

    def cancel(self, *, bond_ref: str) -> SettlementOutcome:
        self._stripe.PaymentIntent.cancel(bond_ref)
        return SettlementOutcome(settlement_id=bond_ref, state="cancelled")
