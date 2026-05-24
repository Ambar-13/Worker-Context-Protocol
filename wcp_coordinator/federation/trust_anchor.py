"""
Bilateral trust anchor: the only piece of cross-coordinator state
WCP v0.955 federation requires.

A trust anchor records:

  - `peer_coordinator_did`: the peer's coordinator DID
  - `peer_public_key`: the peer's Ed25519 public key (32 raw bytes)
  - `peer_endpoint_url`: HTTPS / WSS URL the peer accepts RPCs on
  - `scope`: a set of trust classes the local side will participate in
    with the peer. The three normative classes at v0.955 are
    `capability_discovery`, `reputation_query`, `audit_chain_export`
    (per RFC 0016 as amended at v0.955).
  - `signature`: the peer's Ed25519 signature over the canonical-JSON
    form of the (peer_coordinator_did, peer_endpoint_url, scope,
    established_at, expires_at) tuple. Local side verifies on import.

Trust anchors are stored in-memory by default. Production deployments
back this with a row-level table; the in-memory store is sufficient
for the reference coordinator and the federation demo.
"""
from __future__ import annotations

import base64
import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Iterable, Optional


def _canonical_json(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _ed25519_verify(pubkey_bytes: bytes, data: bytes, signature: str) -> bool:
    """Verify a v0.955 ed25519:<urlsafe-base64> signature against pubkey_bytes."""
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PublicKey,
    )

    if not signature or not signature.startswith("ed25519:"):
        return False
    sig_b64 = signature[len("ed25519:"):]
    pad = "=" * (-len(sig_b64) % 4)
    try:
        sig_bytes = base64.urlsafe_b64decode(sig_b64 + pad)
    except (ValueError, base64.binascii.Error):
        return False
    try:
        Ed25519PublicKey.from_public_bytes(pubkey_bytes).verify(sig_bytes, data)
        return True
    except (InvalidSignature, ValueError):
        return False


SUPPORTED_TRUST_CLASSES = frozenset(
    {"capability_discovery", "reputation_query", "audit_chain_export"}
)


@dataclass(frozen=True)
class TrustAnchor:
    peer_coordinator_did: str
    peer_public_key: bytes  # 32 raw bytes
    peer_endpoint_url: str
    scope: frozenset[str]
    established_at: float  # unix epoch seconds
    expires_at: float
    signature: str  # peer's signature over the canonical body

    def is_expired(self, now: Optional[float] = None) -> bool:
        now = now if now is not None else time.time()
        return now >= self.expires_at

    def allows(self, trust_class: str) -> bool:
        return trust_class in self.scope and not self.is_expired()

    def signed_body(self) -> bytes:
        return _canonical_json(
            {
                "peer_coordinator_did": self.peer_coordinator_did,
                "peer_endpoint_url": self.peer_endpoint_url,
                "scope": sorted(self.scope),
                "established_at": self.established_at,
                "expires_at": self.expires_at,
            }
        )

    def verify_signature(self) -> bool:
        return _ed25519_verify(self.peer_public_key, self.signed_body(), self.signature)

    @classmethod
    def from_dict(cls, d: dict) -> "TrustAnchor":
        scope = frozenset(d["scope"])
        bad = scope - SUPPORTED_TRUST_CLASSES
        if bad:
            raise ValueError(
                f"unknown trust classes in scope: {sorted(bad)}; "
                f"supported: {sorted(SUPPORTED_TRUST_CLASSES)}"
            )
        return cls(
            peer_coordinator_did=d["peer_coordinator_did"],
            peer_public_key=base64.urlsafe_b64decode(d["peer_public_key_b64"]),
            peer_endpoint_url=d["peer_endpoint_url"],
            scope=scope,
            established_at=float(d["established_at"]),
            expires_at=float(d["expires_at"]),
            signature=d["signature"],
        )

    def to_dict(self) -> dict:
        return {
            "peer_coordinator_did": self.peer_coordinator_did,
            "peer_public_key_b64": base64.urlsafe_b64encode(self.peer_public_key)
            .rstrip(b"=")
            .decode("ascii"),
            "peer_endpoint_url": self.peer_endpoint_url,
            "scope": sorted(self.scope),
            "established_at": self.established_at,
            "expires_at": self.expires_at,
            "signature": self.signature,
        }


class TrustAnchorStore:
    """In-memory anchor store keyed by peer_coordinator_did.

    Production deployments swap this for a database-backed store; the
    interface (add, get, lookup_for_url, anchors_for_class) stays the same.
    """

    def __init__(self) -> None:
        self._by_did: dict[str, TrustAnchor] = {}

    def add(self, anchor: TrustAnchor) -> None:
        if not anchor.verify_signature():
            raise ValueError(
                f"trust anchor signature invalid for peer {anchor.peer_coordinator_did}"
            )
        if anchor.is_expired():
            raise ValueError("trust anchor already expired")
        self._by_did[anchor.peer_coordinator_did] = anchor

    def get(self, peer_did: str) -> Optional[TrustAnchor]:
        return self._by_did.get(peer_did)

    def all(self) -> Iterable[TrustAnchor]:
        return list(self._by_did.values())

    def anchors_for_class(self, trust_class: str) -> list[TrustAnchor]:
        return [a for a in self._by_did.values() if a.allows(trust_class)]
