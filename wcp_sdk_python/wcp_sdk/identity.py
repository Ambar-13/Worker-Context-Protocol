"""
Identity primitives: did:wcp creation, signing, verification.

The SDK does not assume any particular key storage; production deployments
SHOULD wrap an HSM, KMS, or platform secure element. The default `generate()`
returns an in-process software keypair suitable for tests and PWA-side use.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from .canonical import canonical_json_bytes

_B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_B58_MAP = {c: i for i, c in enumerate(_B58)}


def _b58encode(b: bytes) -> str:
    n = int.from_bytes(b, "big")
    out = ""
    while n > 0:
        n, r = divmod(n, 58)
        out = _B58[r] + out
    pad = len(b) - len(b.lstrip(b"\x00"))
    return "1" * pad + out


def _b58decode(s: str) -> bytes:
    n = 0
    for c in s:
        if c not in _B58_MAP:
            raise ValueError(f"invalid base58 character: {c!r}")
        n = n * 58 + _B58_MAP[c]
    body = n.to_bytes((n.bit_length() + 7) // 8, "big") if n else b""
    pad = len(s) - len(s.lstrip("1"))
    return b"\x00" * pad + body


def _urlsafe_b64nopad(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")


def did_from_pubkey(pubkey: bytes) -> str:
    """Compute the did:wcp identifier for a 32-byte Ed25519 public key."""
    if len(pubkey) != 32:
        raise ValueError("Ed25519 public key must be 32 bytes")
    return f"did:wcp:{_b58encode(pubkey)}"


def pubkey_from_did(did: str) -> bytes:
    """Recover the 32-byte Ed25519 public key from a did:wcp identifier."""
    if not did.startswith("did:wcp:"):
        raise ValueError(f"not a did:wcp: {did!r}")
    parts = did.split(":", maxsplit=3)
    if len(parts) < 3:
        raise ValueError(f"malformed DID: {did!r}")
    body = parts[2]
    pk = _b58decode(body)
    if len(pk) != 32:
        raise ValueError(
            f"did:wcp identifier must decode to 32-byte Ed25519 pubkey, "
            f"got {len(pk)} bytes"
        )
    return pk


@dataclass(frozen=True)
class _Identity:
    did: str
    public_key_b64url: str
    _key: Ed25519PrivateKey

    def sign(self, payload: Any) -> str:
        sig = self._key.sign(canonical_json_bytes(payload))
        return "ed25519:" + _urlsafe_b64nopad(sig)

    def sign_bytes(self, data: bytes) -> str:
        sig = self._key.sign(data)
        return "ed25519:" + _urlsafe_b64nopad(sig)


class WorkerIdentity(_Identity):
    """A worker's persistent DID identity."""

    @classmethod
    def generate(cls) -> "WorkerIdentity":
        sk = Ed25519PrivateKey.generate()
        return cls._from_sk(sk)

    @classmethod
    def from_private_bytes(cls, raw: bytes) -> "WorkerIdentity":
        return cls._from_sk(Ed25519PrivateKey.from_private_bytes(raw))

    @classmethod
    def load_or_generate(cls, key_path: Path) -> "WorkerIdentity":
        if key_path.exists():
            return cls.from_private_bytes(key_path.read_bytes())
        sk = Ed25519PrivateKey.generate()
        key_path.parent.mkdir(parents=True, exist_ok=True)
        key_path.write_bytes(
            sk.private_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PrivateFormat.Raw,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
        return cls._from_sk(sk)

    @classmethod
    def _from_sk(cls, sk: Ed25519PrivateKey) -> "WorkerIdentity":
        pub = sk.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        did = did_from_pubkey(pub)
        return cls(
            did=did,
            public_key_b64url=_urlsafe_b64nopad(pub),
            _key=sk,
        )


class AgentIdentity(_Identity):
    """An AI-agent-side identity for posting tasks and subscribing."""

    @classmethod
    def generate(cls) -> "AgentIdentity":
        sk = Ed25519PrivateKey.generate()
        pub = sk.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        return cls(
            did=did_from_pubkey(pub),
            public_key_b64url=_urlsafe_b64nopad(pub),
            _key=sk,
        )


def verify_signature(did: str, payload: bytes, signature: str) -> None:
    """Raise ValueError if the signature does not verify against the DID's pubkey."""
    if not signature.startswith("ed25519:"):
        raise ValueError(f"unsupported signature scheme: {signature[:10]!r}")
    sig_b64 = signature[len("ed25519:") :]
    try:
        sig = base64.urlsafe_b64decode(sig_b64 + "==")
    except Exception as exc:
        raise ValueError(f"invalid base64 signature: {exc}") from exc
    pub = pubkey_from_did(did)
    key = Ed25519PublicKey.from_public_bytes(pub)
    try:
        key.verify(sig, payload)
    except InvalidSignature as exc:
        raise ValueError("Ed25519 verify failed") from exc
