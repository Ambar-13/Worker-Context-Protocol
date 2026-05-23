"""Identity and signature tests for the Python SDK."""
from __future__ import annotations

import base64

import pytest

from wcp_sdk.canonical import canonical_json_bytes, sha256_hex
from wcp_sdk.identity import (
    AgentIdentity,
    WorkerIdentity,
    did_from_pubkey,
    pubkey_from_did,
    verify_signature,
)


def test_worker_identity_did_recoverable_from_pubkey():
    ident = WorkerIdentity.generate()
    pub = pubkey_from_did(ident.did)
    assert did_from_pubkey(pub) == ident.did


def test_agent_identity_generate_unique():
    a = AgentIdentity.generate()
    b = AgentIdentity.generate()
    assert a.did != b.did


def test_sign_and_verify_roundtrip():
    ident = WorkerIdentity.generate()
    payload = {"a": 1, "b": [2, 3], "c": "hello"}
    sig = ident.sign(payload)
    verify_signature(ident.did, canonical_json_bytes(payload), sig)


def test_verify_rejects_tampered_payload():
    ident = WorkerIdentity.generate()
    sig = ident.sign({"task_id": "t1"})
    with pytest.raises(ValueError):
        verify_signature(ident.did, canonical_json_bytes({"task_id": "t2"}), sig)


def test_canonical_json_sorts_keys():
    assert canonical_json_bytes({"b": 1, "a": 2}) == b'{"a":2,"b":1}'


def test_sha256_hex_known_vector():
    # "abc" -> ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad
    assert (
        sha256_hex(b"abc")
        == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


def test_load_or_generate_persists(tmp_path):
    p = tmp_path / "k"
    a = WorkerIdentity.load_or_generate(p)
    b = WorkerIdentity.load_or_generate(p)
    assert a.did == b.did
