"""Tests for the hash-linked signed audit chain."""
from __future__ import annotations

from wcp_coordinator.audit_chain import AuditChain, AuditSigner


def test_chain_links(db, signer):
    chain = AuditChain(db, signer)
    r1 = chain.append(
        event_type="task_posted",
        actor_did="did:wcp:agent",
        payload={"task_id": "t1"},
        claim_id="c1",
        task_id="t1",
    )
    r2 = chain.append(
        event_type="task_claimed",
        actor_did="did:wcp:worker",
        payload={"claim_id": "c1"},
        claim_id="c1",
        task_id="t1",
    )
    assert r2.prev_hash == r1.this_hash
    assert chain.verify_chain("c1")


def _seed_two_entries(db, signer):
    """Helper: append two entries on claim c1 and return the model rows."""
    from wcp_coordinator.models import WcpAudit

    chain = AuditChain(db, signer)
    chain.append(
        event_type="task_posted",
        actor_did="did:wcp:agent",
        payload={"task_id": "t1"},
        claim_id="c1",
        task_id="t1",
    )
    chain.append(
        event_type="task_claimed",
        actor_did="did:wcp:worker",
        payload={"claim_id": "c1"},
        claim_id="c1",
        task_id="t1",
    )
    entries = list(
        db.query(WcpAudit).filter(WcpAudit.claim_id == "c1").order_by(
            WcpAudit.timestamp.asc()
        )
    )
    return chain, entries


def test_chain_detects_payload_tamper(db, signer):
    """Modifying payload_json without updating payload_hash is detected.

    At v0.955.1 verify_chain recomputes payload_hash from payload_json, so
    payload-only tampering breaks the chain. Earlier versions only checked
    link structure and would have missed this.
    """
    chain, entries = _seed_two_entries(db, signer)
    entries[0].payload_json = {"task_id": "t1", "tampered": True}
    db.flush()
    assert chain.verify_chain("c1") is False


def test_chain_detects_link_field_tamper(db, signer):
    """Modifying a link field (e.g. event_type) without updating this_hash
    is detected by the link-binding check."""
    chain, entries = _seed_two_entries(db, signer)
    entries[0].event_type = "task_completed"  # was task_posted
    db.flush()
    assert chain.verify_chain("c1") is False


def test_chain_detects_signature_forgery(db, signer):
    """A wrong / forged signature is detected by the signature-validity check."""
    chain, entries = _seed_two_entries(db, signer)
    # Replace with a valid-shaped but wrong signature (sig of a different message).
    entries[0].sig = signer.sign(b"different bytes")
    db.flush()
    assert chain.verify_chain("c1") is False


def test_chain_detects_signature_removal(db, signer):
    """A missing or malformed signature is detected, not silently accepted."""
    chain, entries = _seed_two_entries(db, signer)
    entries[0].sig = ""
    db.flush()
    assert chain.verify_chain("c1") is False


def test_chain_detects_prev_hash_break(db, signer):
    """Snapping the chain by editing prev_hash on a middle entry is detected."""
    chain, entries = _seed_two_entries(db, signer)
    entries[1].prev_hash = "0" * 64
    db.flush()
    assert chain.verify_chain("c1") is False


def test_signer_signs_and_verifies_deterministically(signer):
    s1 = signer.sign(b"hello")
    s2 = signer.sign(b"hello")
    # Ed25519 signatures are deterministic.
    assert s1 == s2
    # Signer can verify its own signature.
    assert signer.verify(b"hello", s1) is True
    # And rejects a signature over different data.
    assert signer.verify(b"goodbye", s1) is False
    # And rejects a malformed sig.
    assert signer.verify(b"hello", "not-a-sig") is False
    assert signer.verify(b"hello", "") is False


def test_verify_accepts_other_signer_pubkey():
    """Two signers with different keys do not validate each other's sigs."""
    a = AuditSigner.ephemeral()
    b = AuditSigner.ephemeral()
    sig_from_a = a.sign(b"payload")
    assert a.verify(b"payload", sig_from_a) is True
    assert b.verify(b"payload", sig_from_a) is False
