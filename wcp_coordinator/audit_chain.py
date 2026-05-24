"""
Hash-linked, signed audit chain for WCP state transitions.

The audit chain is the shared substrate between the human-contractor path
and the robot path. Every state transition (per spec/0.1.md Section 1)
emits one signed AuditChainEntry whose `this_hash` becomes the next
entry's `prev_hash`.

Integrity properties checked by `verify_chain`:

1. **Link continuity** — every entry's `prev_hash` equals the previous
   entry's `this_hash`. Inserting, reordering, or deleting an entry
   breaks the chain.

2. **Link binding** — recomputing `this_hash` from the entry's link
   fields must match the stored value. Modifying any link field
   (event_type, actor_did, timestamp, payload_hash, claim_id, task_id)
   without updating `this_hash` is detected.

3. **Payload binding** — recomputing `payload_hash` from the stored
   `payload_json` must match the stored `payload_hash`. Modifying
   `payload_json` after the fact without updating `payload_hash` is
   detected.

4. **Signature validity** — the entry's `sig` field must verify
   against the signer's public key over the canonical-JSON form of
   the link fields. A forged or removed signature is detected.

Together these defend against an adversary with database write access
who attempts to rewrite history without re-signing.
"""
from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import WcpAudit


def _canonical_json(payload: dict[str, Any]) -> bytes:
    """RFC 8785-compatible canonical JSON for signing/hashing."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class AuditAppendResult:
    entry_id: str
    this_hash: str
    prev_hash: Optional[str]


class AuditChain:
    """Append-only hash-linked audit log.

    Concurrency: per-claim sequence is enforced by reading the latest
    `this_hash` for that claim_id inside the same transaction as the insert.
    Callers MUST hold a row-level lock on the claim (SELECT FOR UPDATE) when
    appending to ensure linearizability under concurrent updates.
    """

    def __init__(self, db: Session, signer: "AuditSigner") -> None:
        self._db = db
        self._signer = signer

    def append(
        self,
        *,
        event_type: str,
        actor_did: str,
        payload: dict[str, Any],
        claim_id: Optional[str] = None,
        task_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ) -> AuditAppendResult:
        ts = timestamp or datetime.now(timezone.utc)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        # Normalize to naive UTC microsecond precision for DB storage so that
        # we get identical isoformat on read (SQLite drops tzinfo on
        # round-trip; PostgreSQL preserves it but we still normalize for
        # cross-backend determinism).
        ts_utc_naive = ts.astimezone(timezone.utc).replace(tzinfo=None)
        ts_canonical = ts_utc_naive.isoformat()

        prev_hash = self._latest_hash_for_claim(claim_id) if claim_id else None
        payload_bytes = _canonical_json(payload)
        payload_hash = _sha256_hex(payload_bytes)
        link_bytes = _canonical_json(
            {
                "event_type": event_type,
                "actor_did": actor_did,
                "timestamp": ts_canonical,
                "payload_hash": payload_hash,
                "prev_hash": prev_hash or "",
                "claim_id": claim_id or "",
                "task_id": task_id or "",
            }
        )
        this_hash = _sha256_hex(link_bytes)
        sig = self._signer.sign(link_bytes)

        entry = WcpAudit(
            claim_id=claim_id,
            task_id=task_id,
            event_type=event_type,
            timestamp=ts_utc_naive,
            actor_did=actor_did,
            payload_json=payload,
            payload_hash=payload_hash,
            prev_hash=prev_hash,
            this_hash=this_hash,
            sig=sig,
        )
        self._db.add(entry)
        self._db.flush()
        return AuditAppendResult(
            entry_id=entry.entry_id,
            this_hash=this_hash,
            prev_hash=prev_hash,
        )

    def _latest_hash_for_claim(self, claim_id: str) -> Optional[str]:
        row = self._db.execute(
            select(WcpAudit.this_hash)
            .where(WcpAudit.claim_id == claim_id)
            .order_by(WcpAudit.timestamp.desc())
            .limit(1)
        ).first()
        return row[0] if row else None

    def verify_chain(self, claim_id: str) -> bool:
        """Walk the chain for `claim_id`; return True if intact.

        Verifies link continuity, link binding, payload binding, and
        the entry signature. See module docstring for the full
        integrity model.
        """
        entries = list(
            self._db.execute(
                select(WcpAudit)
                .where(WcpAudit.claim_id == claim_id)
                .order_by(WcpAudit.timestamp.asc())
            ).scalars()
        )
        prev: Optional[str] = None
        for e in entries:
            # 1. Link continuity: prev_hash must thread through the chain.
            if e.prev_hash != prev:
                return False

            ts = e.timestamp
            if ts.tzinfo is not None:
                ts = ts.astimezone(timezone.utc).replace(tzinfo=None)

            # 3. Payload binding: payload_hash must match a recomputation
            # over the stored payload_json. This catches an adversary who
            # rewrites payload_json without updating payload_hash.
            recomputed_payload_hash = _sha256_hex(_canonical_json(e.payload_json))
            if recomputed_payload_hash != e.payload_hash:
                return False

            link_bytes = _canonical_json(
                {
                    "event_type": e.event_type,
                    "actor_did": e.actor_did,
                    "timestamp": ts.isoformat(),
                    "payload_hash": e.payload_hash,
                    "prev_hash": e.prev_hash or "",
                    "claim_id": e.claim_id or "",
                    "task_id": e.task_id or "",
                }
            )

            # 2. Link binding: this_hash must equal sha256(link_bytes).
            expected = _sha256_hex(link_bytes)
            if expected != e.this_hash:
                return False

            # 4. Signature validity: the stored sig must verify against
            # the signer's public key over link_bytes. Absent or forged
            # signatures fail. The signer is injected at AuditChain
            # construction; we use its public key for verification.
            if not self._signer.verify(link_bytes, e.sig):
                return False

            prev = e.this_hash
        return True


class AuditSigner:
    """Signs and verifies audit chain entries with the coordinator's key.

    v0.1 ships a minimal Ed25519 signer using the `cryptography` library.
    Production deployments inject a KMS-backed signer here.
    """

    _SIG_PREFIX = "ed25519:"

    def __init__(self, private_key_bytes: bytes) -> None:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey,
        )

        self._key = Ed25519PrivateKey.from_private_bytes(private_key_bytes)
        self._public_key = self._key.public_key()

    def sign(self, data: bytes) -> str:
        sig = self._key.sign(data)
        return self._SIG_PREFIX + base64.urlsafe_b64encode(sig).rstrip(b"=").decode("ascii")

    def verify(self, data: bytes, signature: str) -> bool:
        """Return True if `signature` is a valid Ed25519 sig over `data`.

        Accepts the prefixed form produced by `sign` (`ed25519:<b64url>`).
        Returns False for any malformed sig, wrong-algorithm sig, or
        signature that does not verify against the signer's public key.
        Never raises.
        """
        from cryptography.exceptions import InvalidSignature

        if not signature or not signature.startswith(self._SIG_PREFIX):
            return False
        sig_b64 = signature[len(self._SIG_PREFIX):]
        # Re-pad the urlsafe-base64 (we strip `=` on sign for compactness).
        pad = "=" * (-len(sig_b64) % 4)
        try:
            sig_bytes = base64.urlsafe_b64decode(sig_b64 + pad)
        except (ValueError, base64.binascii.Error):
            return False
        try:
            self._public_key.verify(sig_bytes, data)
            return True
        except InvalidSignature:
            return False

    @classmethod
    def ephemeral(cls) -> "AuditSigner":
        """Test-only: generate a fresh signer with a new ephemeral key."""
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey,
        )
        from cryptography.hazmat.primitives import serialization

        sk = Ed25519PrivateKey.generate()
        raw = sk.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
        return cls(raw)
