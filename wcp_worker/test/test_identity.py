"""Unit tests for wcp_worker.identity (ROS 2-independent)."""
from __future__ import annotations

from pathlib import Path

from wcp_worker.identity import WorkerIdentity, canonical_json


def test_load_or_generate_persists_key(tmp_path: Path) -> None:
    key_path = tmp_path / "key"
    a = WorkerIdentity.load_or_generate(key_path)
    b = WorkerIdentity.load_or_generate(key_path)
    assert a.did == b.did
    assert a.public_key_b64url == b.public_key_b64url


def test_sign_and_did_consistency(tmp_path: Path) -> None:
    key_path = tmp_path / "key"
    ident = WorkerIdentity.load_or_generate(key_path)
    assert ident.did.startswith("did:wcp:")
    sig = ident.sign({"task_id": "t1"})
    assert sig.startswith("ed25519:")


def test_canonical_json_sorts_keys() -> None:
    a = canonical_json({"b": 1, "a": 2})
    b = canonical_json({"a": 2, "b": 1})
    assert a == b
    assert a == b'{"a":2,"b":1}'
