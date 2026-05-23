"""
did:wcp resolver.

The v0.1 method-spec (spec/did-method-wcp.md) binds the identifier to the
base58-encoded Ed25519 public key of the controlling keypair. Resolution is
inline: the public key is recoverable from the identifier without any
external lookup.

For production-grade reputation queries, coordinators MAY publish DID documents
to a `/.well-known/did-wcp/<id>` endpoint; the resolver here is the minimal
inline form sufficient for signature verification.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Optional

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

# Base58 alphabet (base58btc per Multibase RFC; standard encoding for W3C
# DID methods that carry raw cryptographic identifier bytes). Excludes 0,
# O, I, l for visual disambiguation. See spec/did-method-wcp.md and RFC 0031.
_B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_B58_MAP = {c: i for i, c in enumerate(_B58)}


def _b58decode(s: str) -> bytes:
    n = 0
    for c in s:
        if c not in _B58_MAP:
            raise ValueError(f"invalid base58 character: {c!r}")
        n = n * 58 + _B58_MAP[c]
    full = n.to_bytes((n.bit_length() + 7) // 8, "big") if n else b""
    pad = len(s) - len(s.lstrip("1"))
    return b"\x00" * pad + full


def _b58encode(b: bytes) -> str:
    n = int.from_bytes(b, "big")
    out = ""
    while n:
        n, r = divmod(n, 58)
        out = _B58[r] + out
    pad = len(b) - len(b.lstrip(b"\x00"))
    return "1" * pad + out


@dataclass(frozen=True)
class ResolvedDID:
    did: str
    public_key: bytes
    path: Optional[str] = None


class DIDResolutionError(Exception):
    """Raised when a DID cannot be parsed or resolved."""


class SignatureVerificationError(Exception):
    """Raised when a signature does not verify against the resolved DID."""


class DidResolver:
    """Inline did:wcp resolver.

    Use:
        r = DidResolver()
        resolved = r.resolve("did:wcp:8FCQ...")
        r.verify(resolved, payload_bytes, signature_b64)
    """

    METHOD = "wcp"

    def resolve(self, did: str) -> ResolvedDID:
        if not did.startswith("did:"):
            raise DIDResolutionError(f"not a DID: {did!r}")
        parts = did.split(":", maxsplit=3)
        if len(parts) < 3 or parts[1] != self.METHOD:
            raise DIDResolutionError(f"not a did:{self.METHOD}: {did!r}")
        identifier = parts[2]
        path = parts[3] if len(parts) == 4 else None
        try:
            pubkey = _b58decode(identifier)
        except ValueError as exc:
            raise DIDResolutionError(f"invalid identifier: {exc}") from exc
        if len(pubkey) != 32:
            raise DIDResolutionError(
                f"did:wcp identifier must decode to 32-byte Ed25519 pubkey, "
                f"got {len(pubkey)} bytes"
            )
        return ResolvedDID(did=did, public_key=pubkey, path=path)

    def verify(
        self, resolved: ResolvedDID, payload: bytes, signature: str
    ) -> None:
        """Raise SignatureVerificationError if invalid; return None if valid."""
        if not signature.startswith("ed25519:"):
            raise SignatureVerificationError(
                f"unsupported signature scheme: {signature[:10]!r}"
            )
        sig_b64 = signature[len("ed25519:") :]
        try:
            sig = base64.urlsafe_b64decode(sig_b64 + "==")
        except Exception as exc:
            raise SignatureVerificationError(
                f"invalid base64 signature: {exc}"
            ) from exc
        key = Ed25519PublicKey.from_public_bytes(resolved.public_key)
        try:
            key.verify(sig, payload)
        except InvalidSignature as exc:
            raise SignatureVerificationError("Ed25519 verify failed") from exc

    def did_from_pubkey(self, pubkey: bytes) -> str:
        if len(pubkey) != 32:
            raise ValueError("Ed25519 public key must be 32 bytes")
        return f"did:wcp:{_b58encode(pubkey)}"
