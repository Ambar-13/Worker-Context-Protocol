"""Ed25519 DID keypair management for the WCP worker plugin.

Mirrors the backend's did:wcp method spec (spec/did-method-wcp.md). The
plugin loads a persisted keypair from disk on startup, or generates one on
first boot and writes it under a config-provided path. Production deployments
SHOULD use a TPM- or secure-element-backed implementation; a software
keypair is acceptable at v0.1 with the trust class declared in the
CapabilityDescriptor.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

_B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def _b58encode(b: bytes) -> str:
    n = int.from_bytes(b, "big")
    out = ""
    while n > 0:
        n, r = divmod(n, 58)
        out = _B58[r] + out
    pad = len(b) - len(b.lstrip(b"\x00"))
    return "1" * pad + out


def _urlsafe_b64nopad(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")


def canonical_json(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


class WorkerIdentity:
    """Worker's persistent DID identity for the WCP plugin."""

    def __init__(self, private_key: Ed25519PrivateKey) -> None:
        self._key = private_key
        pub = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        self._pubkey_bytes = pub
        self.did = f"did:wcp:{_b58encode(pub)}"

    @classmethod
    def load_or_generate(cls, key_path: Path) -> "WorkerIdentity":
        key_path.parent.mkdir(parents=True, exist_ok=True)
        if key_path.exists():
            raw = key_path.read_bytes()
            return cls(Ed25519PrivateKey.from_private_bytes(raw))
        sk = Ed25519PrivateKey.generate()
        raw = sk.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
        key_path.write_bytes(raw)
        os.chmod(key_path, 0o600)
        return cls(sk)

    @property
    def public_key_b64url(self) -> str:
        return _urlsafe_b64nopad(self._pubkey_bytes)

    def sign(self, payload: dict[str, Any]) -> str:
        sig = self._key.sign(canonical_json(payload))
        return "ed25519:" + _urlsafe_b64nopad(sig)

    def sign_bytes(self, data: bytes) -> str:
        sig = self._key.sign(data)
        return "ed25519:" + _urlsafe_b64nopad(sig)
