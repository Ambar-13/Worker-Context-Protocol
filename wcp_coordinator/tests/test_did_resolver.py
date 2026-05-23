"""Tests for did_resolver."""
from __future__ import annotations

import base64

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from wcp_coordinator.did_resolver import (
    DIDResolutionError,
    DidResolver,
    SignatureVerificationError,
    _b58decode,
    _b58encode,
)


def test_resolve_valid_did():
    sk = Ed25519PrivateKey.generate()
    pub = sk.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    did = f"did:wcp:{_b58encode(pub)}"
    r = DidResolver()
    resolved = r.resolve(did)
    assert resolved.did == did
    assert resolved.public_key == pub


def test_resolve_rejects_other_method():
    r = DidResolver()
    with pytest.raises(DIDResolutionError):
        r.resolve("did:key:xyz")


def test_resolve_rejects_bad_identifier():
    r = DidResolver()
    with pytest.raises(DIDResolutionError):
        r.resolve("did:wcp:0OIl")  # not valid base58


def test_verify_valid_signature():
    sk = Ed25519PrivateKey.generate()
    pub = sk.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    did = f"did:wcp:{_b58encode(pub)}"
    payload = b'{"hello":"world"}'
    sig = sk.sign(payload)
    sig_str = "ed25519:" + base64.urlsafe_b64encode(sig).rstrip(b"=").decode("ascii")
    r = DidResolver()
    resolved = r.resolve(did)
    r.verify(resolved, payload, sig_str)  # should not raise


def test_verify_rejects_tampered_payload():
    sk = Ed25519PrivateKey.generate()
    pub = sk.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    did = f"did:wcp:{_b58encode(pub)}"
    payload = b'{"hello":"world"}'
    sig = sk.sign(payload)
    sig_str = "ed25519:" + base64.urlsafe_b64encode(sig).rstrip(b"=").decode("ascii")
    r = DidResolver()
    resolved = r.resolve(did)
    with pytest.raises(SignatureVerificationError):
        r.verify(resolved, payload + b"x", sig_str)


def test_base58_roundtrip():
    for n in [0, 1, 255, 12345, 2**256 - 1]:
        b = n.to_bytes((n.bit_length() + 7) // 8 or 1, "big")
        assert _b58decode(_b58encode(b)) == b
