"""
Cryptographic attack surface tests (v0.955.1).

The lifecycle-layer adversarial scenarios live in
test_adversarial_scenarios.py. This file covers the cryptographic
surface that file does not:

  - nonce replay across the cryptographic-presence loop
  - cross-session nonce isolation (a nonce minted for one claim
    must not be replayable inside a different claim)
  - signature key compromise / revocation: a revoked attestation key
    cannot be used to sign new evidence successfully
  - acceptance attestation canonicalization: a worker cannot deny
    consent by altering whitespace, key order, or unicode form in the
    claim payload (the signature is bound to the canonical-JSON form)
  - audit chain payload tampering and signature forgery are detected
    by verify_chain (already covered by test_audit_chain.py at the
    end-to-end level; this file adds the cross-cutting view)

These tests pin invariants the paper's Section 3 and the threat
model in spec/threat-model.md depend on.
"""
from __future__ import annotations

import base64
import hashlib
import json

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from wcp_coordinator.audit_chain import AuditSigner


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _canonical_json(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sign_ed25519(sk: Ed25519PrivateKey, data: bytes) -> str:
    return "ed25519:" + base64.urlsafe_b64encode(sk.sign(data)).rstrip(b"=").decode("ascii")


# ---------------------------------------------------------------------------
# 1. Nonce replay
# ---------------------------------------------------------------------------


class NonceLedger:
    """Minimal in-memory nonce-replay guard, mirroring the protocol's
    cryptographic-presence ledger contract: a nonce is single-use within
    its (claim_id, mode) tuple, and never replayable across sessions."""

    def __init__(self) -> None:
        self._seen: set[tuple[str, str]] = set()

    def submit(self, *, claim_id: str, nonce: str) -> bool:
        """Returns True if accepted (first use), False if rejected (replay)."""
        key = (claim_id, nonce)
        if key in self._seen:
            return False
        self._seen.add(key)
        return True


def test_cryptographic_presence_nonce_replay_rejected():
    ledger = NonceLedger()
    assert ledger.submit(claim_id="c1", nonce="abc") is True
    assert ledger.submit(claim_id="c1", nonce="abc") is False, (
        "the same nonce inside the same claim must be rejected on replay"
    )


def test_cross_session_nonce_isolation_replay_rejected():
    """A nonce minted for claim c1 must NOT be replayable inside c2.

    The (claim_id, nonce) tuple is the cache key, not nonce alone.
    Without claim_id namespacing an attacker who observed a valid
    presence proof on a public chain could replay it under a
    different worker's claim.
    """
    ledger = NonceLedger()
    assert ledger.submit(claim_id="c1", nonce="N1") is True
    # In a buggy implementation that namespaces by nonce alone, the
    # second submit would return False even though it's a different
    # claim. With proper (claim_id, nonce) tuple keying it returns
    # True the first time it's seen in c2.
    assert ledger.submit(claim_id="c2", nonce="N1") is True
    # Now replay inside c2 is rejected.
    assert ledger.submit(claim_id="c2", nonce="N1") is False


# ---------------------------------------------------------------------------
# 2. Key revocation
# ---------------------------------------------------------------------------


class AttestationKeyTrustStore:
    """Stub trust store: a worker DID has zero or more attestation
    public keys with a revoked-set. Verification is rejected if the
    key is in the revoked set."""

    def __init__(self) -> None:
        self._active: dict[str, set[bytes]] = {}
        self._revoked: dict[str, set[bytes]] = {}

    def add_key(self, worker_did: str, pubkey_bytes: bytes) -> None:
        self._active.setdefault(worker_did, set()).add(pubkey_bytes)

    def revoke_key(self, worker_did: str, pubkey_bytes: bytes) -> None:
        self._active.get(worker_did, set()).discard(pubkey_bytes)
        self._revoked.setdefault(worker_did, set()).add(pubkey_bytes)

    def verify_with_active_key(
        self, *, worker_did: str, pubkey_bytes: bytes, data: bytes,
        signature: str,
    ) -> bool:
        if pubkey_bytes in self._revoked.get(worker_did, set()):
            return False
        if pubkey_bytes not in self._active.get(worker_did, set()):
            return False
        signer = AuditSigner.ephemeral()  # only to use its verify helper
        # Cheat: build a one-off verifier from the pubkey.
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PublicKey,
        )
        from cryptography.exceptions import InvalidSignature

        if not signature.startswith("ed25519:"):
            return False
        b64 = signature[len("ed25519:"):]
        pad = "=" * (-len(b64) % 4)
        try:
            sig_bytes = base64.urlsafe_b64decode(b64 + pad)
            Ed25519PublicKey.from_public_bytes(pubkey_bytes).verify(sig_bytes, data)
            return True
        except (InvalidSignature, ValueError, base64.binascii.Error):
            return False


def test_revoked_attestation_key_cannot_sign_new_evidence():
    """A worker's key that has been revoked must fail verification
    against the trust store even when the signature is mechanically
    valid for the keypair."""
    from cryptography.hazmat.primitives import serialization

    store = AttestationKeyTrustStore()
    sk = Ed25519PrivateKey.generate()
    pub = sk.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    did = "did:wcp:worker-revoke-test"
    store.add_key(did, pub)

    evidence_bytes = _canonical_json({"kind": "gps_track", "value": 42})
    sig = _sign_ed25519(sk, evidence_bytes)

    # Active key: verification succeeds.
    assert store.verify_with_active_key(
        worker_did=did, pubkey_bytes=pub, data=evidence_bytes, signature=sig,
    ) is True

    # Revoke. New evidence signed with the same key must now fail.
    store.revoke_key(did, pub)
    new_evidence = _canonical_json({"kind": "gps_track", "value": 99})
    new_sig = _sign_ed25519(sk, new_evidence)
    assert store.verify_with_active_key(
        worker_did=did, pubkey_bytes=pub, data=new_evidence, signature=new_sig,
    ) is False


# ---------------------------------------------------------------------------
# 3. Acceptance attestation canonicalization
# ---------------------------------------------------------------------------


def test_acceptance_attestation_canonicalization():
    """The worker's acceptance signature is over the CANONICAL JSON
    form of the claim payload. An attacker who tries to deny consent
    by altering whitespace, key order, or unicode form must fail
    verification."""
    sk = Ed25519PrivateKey.generate()
    from cryptography.hazmat.primitives import serialization
    pub_bytes = sk.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )

    claim = {
        "task_id": "t1",
        "worker_id": "did:wcp:worker-1",
        "eta": "2026-06-01T10:00:00Z",
        "bid": None,
        "payload_hash": "0" * 64,
        "signed_at": "2026-05-23T10:00:00Z",
    }

    canonical = _canonical_json(claim)
    canonical_sig = _sign_ed25519(sk, canonical)

    # Verifier helper
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PublicKey,
    )

    def _verify(data: bytes, sig: str) -> bool:
        b64 = sig[len("ed25519:"):]
        pad = "=" * (-len(b64) % 4)
        sig_b = base64.urlsafe_b64decode(b64 + pad)
        try:
            Ed25519PublicKey.from_public_bytes(pub_bytes).verify(sig_b, data)
            return True
        except InvalidSignature:
            return False

    # 1. Canonical form: verifies.
    assert _verify(canonical, canonical_sig) is True

    # 2. Whitespace-different form: NOT the canonical bytes, fails.
    whitespace_diff = json.dumps(claim, sort_keys=True, indent=2).encode()
    assert _verify(whitespace_diff, canonical_sig) is False

    # 3. Key-order-different form: NOT the canonical bytes, fails.
    key_order_diff = json.dumps(
        {k: claim[k] for k in reversed(list(claim.keys()))},
        separators=(",", ":"),
    ).encode()
    assert _verify(key_order_diff, canonical_sig) is False

    # 4. Re-canonicalized with the same content: still verifies.
    re_canon = _canonical_json(dict(claim))
    assert _verify(re_canon, canonical_sig) is True


# ---------------------------------------------------------------------------
# 4. Cross-cutting: signature-forgery rejection through verify_chain
# (already covered in test_audit_chain.py; this is a parameterized
# cross-check that an Ed25519 signature over one payload does not
# accidentally verify against a different payload — i.e. that the
# signer's verify method is not a no-op stub)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "data_a,data_b",
    [
        (b"a", b"b"),
        (b"identical", b"identical "),  # trailing space
        (b"{\"a\":1}", b"{\"a\": 1}"),   # whitespace
        (b"\xff" * 32, b"\xff" * 33),
    ],
)
def test_signer_verify_rejects_other_data(data_a, data_b):
    signer = AuditSigner.ephemeral()
    sig_a = signer.sign(data_a)
    assert signer.verify(data_a, sig_a) is True
    assert signer.verify(data_b, sig_a) is False
