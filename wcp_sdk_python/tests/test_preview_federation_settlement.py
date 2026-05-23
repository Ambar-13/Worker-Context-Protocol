"""Tests for wcp_sdk.preview.federation_settlement (RFC 0032 preview)."""
from __future__ import annotations

import pytest

from wcp_sdk.preview.federation_settlement import (
    Amount,
    FederationSettlementTransfer,
    SettlementModel,
    TransferProofRef,
    TransferProofType,
    build_dispute_recovery_policy,
    emit_transfer,
    new_transfer_id,
    verify_transfer,
)


def _make_proof() -> TransferProofRef:
    return TransferProofRef(
        type=TransferProofType.STRIPE_CONNECT_TRANSFER,
        id="tr_demo",
        issued_at="2026-05-23T12:00:00Z",
        verification_endpoint="https://provider.test/verify/tr_demo",
    )


def test_emit_transfer_creates_v11_audit_entry():
    entry = emit_transfer(
        task_id="task-1",
        claim_id="claim-1",
        sender_coordinator_did="did:wcp:zCoordA",
        receiver_coordinator_did="did:wcp:zCoordB",
        amount=Amount(currency="USD", value="125.50"),
        transfer_proof_ref=_make_proof(),
    )
    assert entry.kind == "federation-settlement-transfer"
    assert entry.schema_version == "wcp/1.1"
    assert entry.entry_hash != ""  # computed


def test_verify_transfer_accepts_well_formed():
    entry = emit_transfer(
        task_id="task-1",
        claim_id="claim-1",
        sender_coordinator_did="did:wcp:zCoordA",
        receiver_coordinator_did="did:wcp:zCoordB",
        amount=Amount(currency="USD", value="50.00"),
        transfer_proof_ref=_make_proof(),
    )
    ok, reason = verify_transfer(entry)
    assert ok is True
    assert reason == "accepted"


def test_verify_transfer_detects_tampered_hash():
    entry = emit_transfer(
        task_id="task-1",
        claim_id="claim-1",
        sender_coordinator_did="did:wcp:zCoordA",
        receiver_coordinator_did="did:wcp:zCoordB",
        amount=Amount(currency="USD", value="50.00"),
        transfer_proof_ref=_make_proof(),
    )
    # Tamper with the entry after hash was computed
    entry.amount = Amount(currency="USD", value="50000.00")
    ok, reason = verify_transfer(entry)
    assert ok is False
    assert "entry_hash" in reason


def test_verify_transfer_expected_sender_mismatch():
    entry = emit_transfer(
        task_id="task-1",
        claim_id="claim-1",
        sender_coordinator_did="did:wcp:zCoordA",
        receiver_coordinator_did="did:wcp:zCoordB",
        amount=Amount(currency="USD", value="50.00"),
        transfer_proof_ref=_make_proof(),
    )
    ok, reason = verify_transfer(
        entry, expected_sender_coordinator_did="did:wcp:zWrongCoord"
    )
    assert ok is False
    assert "sender mismatch" in reason


def test_verify_transfer_expected_amount_mismatch():
    entry = emit_transfer(
        task_id="task-1",
        claim_id="claim-1",
        sender_coordinator_did="did:wcp:zCoordA",
        receiver_coordinator_did="did:wcp:zCoordB",
        amount=Amount(currency="USD", value="50.00"),
        transfer_proof_ref=_make_proof(),
    )
    ok, reason = verify_transfer(entry, expected_amount=Amount("EUR", "50.00"))
    assert ok is False
    assert "amount mismatch" in reason


def test_verify_transfer_missing_fields():
    incomplete = FederationSettlementTransfer(
        task_id="",
        claim_id="claim-1",
        sender_coordinator_did="did:wcp:zCoordA",
        receiver_coordinator_did="did:wcp:zCoordB",
        amount=Amount("USD", "10.00"),
        transfer_proof_ref=_make_proof(),
    )
    incomplete.entry_hash = incomplete.compute_entry_hash()
    ok, reason = verify_transfer(incomplete)
    assert ok is False
    assert "task_id" in reason or "claim_id" in reason


def test_transfer_proof_ref_to_dict_omits_optional_when_absent():
    ref = TransferProofRef(
        type=TransferProofType.BANK_WIRE_RECEIPT,
        id="wire-001",
        issued_at="2026-05-23T12:00:00Z",
    )
    out = ref.to_dict()
    assert "verification_endpoint" not in out


def test_transfer_proof_ref_to_dict_includes_optional_when_present():
    ref = _make_proof()
    out = ref.to_dict()
    assert out["verification_endpoint"] == "https://provider.test/verify/tr_demo"


def test_amount_to_dict():
    a = Amount(currency="USD", value="100.00")
    assert a.to_dict() == {"currency": "USD", "value": "100.00"}


def test_build_dispute_recovery_policy_default():
    policy = build_dispute_recovery_policy()
    assert policy["option"] == "A-holdback"
    assert policy["holdback_fraction"] == 0.2
    assert policy["holdback_until_dispute_window_closes"] is True


def test_build_dispute_recovery_policy_custom():
    policy = build_dispute_recovery_policy(
        holdback_fraction=0.5, holdback_until_dispute_window_closes=False
    )
    assert policy["holdback_fraction"] == 0.5
    assert policy["holdback_until_dispute_window_closes"] is False


def test_build_dispute_recovery_policy_rejects_out_of_range():
    with pytest.raises(ValueError, match="between 0 and 1"):
        build_dispute_recovery_policy(holdback_fraction=1.5)


def test_new_transfer_id_format():
    tid = new_transfer_id()
    assert tid.startswith("tr_")
    assert len(tid) == 19  # "tr_" + 16 hex chars
    assert tid != new_transfer_id()  # uniqueness


def test_settlement_model_enum_values():
    assert SettlementModel.A_CAPTURE_B_PAYOUT_OOB.value.startswith("model-i")
    assert SettlementModel.A_CAPTURE_ONCHAIN_TRANSFER_B_PAYOUT.value.startswith(
        "model-ii"
    )
    assert SettlementModel.SHARED_ESCROW_PROVIDER.value.startswith("model-iii")


def test_transfer_proof_type_enum_values():
    assert TransferProofType.STRIPE_CONNECT_TRANSFER.value == "stripe-connect-transfer"
    assert TransferProofType.ONCHAIN_TX_HASH.value == "onchain-tx-hash"


def test_entry_hash_deterministic():
    args = dict(
        task_id="t1",
        claim_id="c1",
        sender_coordinator_did="did:wcp:zA",
        receiver_coordinator_did="did:wcp:zB",
        amount=Amount("USD", "1.00"),
        transfer_proof_ref=TransferProofRef(
            type=TransferProofType.ONCHAIN_TX_HASH,
            id="0xdead",
            issued_at="2026-05-23T12:00:00Z",
        ),
    )
    e1 = emit_transfer(**args)
    e2 = emit_transfer(**args)
    assert e1.entry_hash == e2.entry_hash
