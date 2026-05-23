"""
RFC 0032 preview: Cross-Coordinator Settlement Clearing.

Provides:
- FederationSettlementTransfer audit entry type
- emit_transfer(...) helper for Coordinator A side (sender of funds)
- verify_transfer(...) helper for Coordinator B side (receiver)
- enum of the three settlement-clearing models (i, ii, iii)

Model (ii) is the recommended v1.1 primitive: A-side capture + on-chain
transfer with verifiable receipt + B-side payout. The audit chain on both
coordinators records a `federation-settlement-transfer` entry referencing
the same transfer_proof_ref.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from . import emit_preview_warning


class SettlementModel(str, Enum):
    """The three settlement-clearing models analyzed in RFC 0032."""

    A_CAPTURE_B_PAYOUT_OOB = "model-i-a-capture-b-payout-out-of-band"
    A_CAPTURE_ONCHAIN_TRANSFER_B_PAYOUT = "model-ii-a-capture-onchain-transfer-b-payout"
    SHARED_ESCROW_PROVIDER = "model-iii-shared-escrow-provider"


class TransferProofType(str, Enum):
    """Recognized types of transfer_proof_ref in the audit entry."""

    STRIPE_CONNECT_TRANSFER = "stripe-connect-transfer"
    BANK_WIRE_RECEIPT = "bank-wire-receipt"
    ONCHAIN_TX_HASH = "onchain-tx-hash"
    ESCROW_PROVIDER_RECEIPT = "escrow-provider-receipt"
    OTHER = "other"


@dataclass
class TransferProofRef:
    """Reference to the transfer's external proof."""

    type: TransferProofType
    id: str
    issued_at: str  # RFC 3339
    verification_endpoint: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        out = {
            "type": self.type.value,
            "id": self.id,
            "issued_at": self.issued_at,
        }
        if self.verification_endpoint:
            out["verification_endpoint"] = self.verification_endpoint
        return out


@dataclass
class Amount:
    """Currency and decimal value pair."""

    currency: str
    value: str  # decimal string per spec/1.0-rc1.md Section 5

    def to_dict(self) -> dict[str, Any]:
        return {"currency": self.currency, "value": self.value}


@dataclass
class FederationSettlementTransfer:
    """The audit chain entry kind introduced by RFC 0032.

    Embed in audit chain on both Coordinator A (sender) and Coordinator B
    (receiver). Both entries reference the same transfer_proof_ref so
    cross-coordinator audit verification (spec/federation.md Section 4)
    can detect divergence.
    """

    kind: str = field(default="federation-settlement-transfer", init=False)
    schema_version: str = field(default="wcp/1.1", init=False)
    task_id: str = ""
    claim_id: str = ""
    sender_coordinator_did: str = ""
    receiver_coordinator_did: str = ""
    amount: Optional[Amount] = None
    transfer_proof_ref: Optional[TransferProofRef] = None
    previous_entry_hash: Optional[str] = None
    entry_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "kind": self.kind,
            "schema_version": self.schema_version,
            "task_id": self.task_id,
            "claim_id": self.claim_id,
            "sender_coordinator_did": self.sender_coordinator_did,
            "receiver_coordinator_did": self.receiver_coordinator_did,
        }
        if self.amount:
            out["amount"] = self.amount.to_dict()
        if self.transfer_proof_ref:
            out["transfer_proof_ref"] = self.transfer_proof_ref.to_dict()
        if self.previous_entry_hash is not None:
            out["previous_entry_hash"] = self.previous_entry_hash
        return out

    def compute_entry_hash(self) -> str:
        canonical = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def emit_transfer(
    *,
    task_id: str,
    claim_id: str,
    sender_coordinator_did: str,
    receiver_coordinator_did: str,
    amount: Amount,
    transfer_proof_ref: TransferProofRef,
    previous_entry_hash: Optional[str] = None,
) -> FederationSettlementTransfer:
    """Coordinator A side: construct a FederationSettlementTransfer audit entry.

    The returned object is ready to append to A's audit chain. After capture
    settles successfully via the escrow provider, A emits this entry; A's
    federation router pushes the entry to Coordinator B for inclusion in B's
    audit chain. Both coordinators MUST hold the entry with matching
    transfer_proof_ref.
    """
    emit_preview_warning(32, "federation_settlement")
    entry = FederationSettlementTransfer(
        task_id=task_id,
        claim_id=claim_id,
        sender_coordinator_did=sender_coordinator_did,
        receiver_coordinator_did=receiver_coordinator_did,
        amount=amount,
        transfer_proof_ref=transfer_proof_ref,
        previous_entry_hash=previous_entry_hash,
    )
    entry.entry_hash = entry.compute_entry_hash()
    return entry


def verify_transfer(
    entry: FederationSettlementTransfer,
    *,
    expected_sender_coordinator_did: Optional[str] = None,
    expected_amount: Optional[Amount] = None,
) -> tuple[bool, str]:
    """Coordinator B side: verify the federation-settlement-transfer entry.

    Returns (accepted, reason). Production deployments also call the
    transfer_proof_ref.verification_endpoint to confirm the receipt
    cryptographically; this preview verifies only the entry's structural
    properties.
    """
    emit_preview_warning(32, "federation_settlement")
    if entry.kind != "federation-settlement-transfer":
        return False, f"unexpected entry kind: {entry.kind!r}"
    if not entry.task_id or not entry.claim_id:
        return False, "missing task_id or claim_id"
    if not entry.sender_coordinator_did or not entry.receiver_coordinator_did:
        return False, "missing sender or receiver coordinator DID"
    if not entry.amount:
        return False, "missing amount"
    if not entry.transfer_proof_ref:
        return False, "missing transfer_proof_ref"
    if expected_sender_coordinator_did and (
        entry.sender_coordinator_did != expected_sender_coordinator_did
    ):
        return (
            False,
            (
                f"sender mismatch: expected {expected_sender_coordinator_did!r}, "
                f"got {entry.sender_coordinator_did!r}"
            ),
        )
    if expected_amount and (
        entry.amount.currency != expected_amount.currency
        or entry.amount.value != expected_amount.value
    ):
        return (
            False,
            (
                f"amount mismatch: expected {expected_amount.to_dict()!r}, "
                f"got {entry.amount.to_dict()!r}"
            ),
        )
    # Verify hash integrity
    expected_hash = entry.compute_entry_hash()
    if entry.entry_hash != expected_hash:
        return False, "entry_hash mismatch (tampered or recomputation mismatch)"
    return True, "accepted"


def build_dispute_recovery_policy(
    *,
    holdback_fraction: float = 0.2,
    holdback_until_dispute_window_closes: bool = True,
) -> dict[str, Any]:
    """Build the federation trust anchor's dispute recovery policy.

    See RFC 0032 section "Dispute window semantics" for the two options.
    Option A: B holds back a fraction of payout for the dispute window.
    Option B: Federation-level insurance pool (v1.2 candidate).

    This helper returns Option A's policy. Returns a dict embeddable in the
    federation trust anchor declaration.
    """
    emit_preview_warning(32, "federation_settlement")
    if not 0.0 <= holdback_fraction <= 1.0:
        raise ValueError(
            f"holdback_fraction must be between 0 and 1, got {holdback_fraction}"
        )
    return {
        "option": "A-holdback",
        "holdback_fraction": holdback_fraction,
        "holdback_until_dispute_window_closes": holdback_until_dispute_window_closes,
    }


def new_transfer_id() -> str:
    """Generate a unique transfer ID for use in transfer_proof_ref.id."""
    return "tr_" + uuid.uuid4().hex[:16]
