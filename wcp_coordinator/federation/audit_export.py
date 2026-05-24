"""
Federation audit-chain interop.

When a local agent wants to verify that a task it forwarded actually
completed on a peer, the AuditExport fetches the peer's audit chain
segment for that claim_id, walks it, and records a local
`federation_audit_chain_imported` entry with the segment's terminal
hash.

The fetcher is pluggable so tests can supply an in-memory peer chain.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Awaitable, Callable, Optional

from .trust_anchor import TrustAnchor


# Async (peer_url, claim_id) -> list of audit-chain entries (each a dict).
ChainFetcher = Callable[[str, str], Awaitable[list[dict[str, Any]]]]


def _canonical_json(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_chain_segment(entries: list[dict[str, Any]]) -> bool:
    """Verify link continuity, link binding, and payload binding over a
    peer chain segment expressed as plain dicts. Signature verification
    requires the peer's signer pubkey and is checked elsewhere.

    The first entry's `prev_hash` may be either absent, None, or "" —
    they are all treated as 'no predecessor'.
    """
    prev: Optional[str] = None
    for e in entries:
        # Normalize empty-string and None to the same "no predecessor".
        observed_prev = e.get("prev_hash") or None
        if observed_prev != prev:
            return False

        payload_bytes = _canonical_json(e.get("payload_json") or {})
        if _sha256_hex(payload_bytes) != e.get("payload_hash"):
            return False

        link_bytes = _canonical_json(
            {
                "event_type": e.get("event_type"),
                "actor_did": e.get("actor_did"),
                "timestamp": e.get("timestamp"),
                "payload_hash": e.get("payload_hash"),
                "prev_hash": e.get("prev_hash") or "",
                "claim_id": e.get("claim_id") or "",
                "task_id": e.get("task_id") or "",
            }
        )
        if _sha256_hex(link_bytes) != e.get("this_hash"):
            return False

        prev = e.get("this_hash")
    return True


class AuditExport:
    def __init__(self, audit, fetcher: Optional[ChainFetcher] = None) -> None:
        self._audit = audit
        self._fetcher = fetcher

    def with_fetcher(self, fetcher: ChainFetcher) -> "AuditExport":
        self._fetcher = fetcher
        return self

    async def import_peer_chain(
        self,
        *,
        peer: TrustAnchor,
        claim_id: str,
    ) -> dict[str, Any]:
        """Fetch and verify a peer chain segment for `claim_id`.

        Returns {"ok": bool, "entries": int, "terminal_hash": str | None,
        "completion_event": str | None}.
        """
        if not peer.allows("audit_chain_export"):
            return {
                "ok": False,
                "reason": "peer trust anchor does not allow audit_chain_export",
                "entries": 0,
                "terminal_hash": None,
                "completion_event": None,
            }
        if self._fetcher is None:
            raise RuntimeError("AuditExport has no fetcher configured")

        entries = await self._fetcher(peer.peer_endpoint_url, claim_id)
        ok = verify_chain_segment(entries)
        terminal_hash = entries[-1]["this_hash"] if entries else None
        completion_event = next(
            (e["event_type"] for e in reversed(entries)
             if e.get("event_type") in
                ("task_completed", "task_voided", "task_aborted")),
            None,
        )

        self._audit.append(
            event_type="federation_audit_chain_imported",
            actor_did=peer.peer_coordinator_did,
            payload={
                "peer_coordinator_did": peer.peer_coordinator_did,
                "claim_id": claim_id,
                "entries": len(entries),
                "terminal_hash": terminal_hash,
                "completion_event": completion_event,
                "ok": ok,
            },
            claim_id=claim_id,
        )

        return {
            "ok": ok,
            "entries": len(entries),
            "terminal_hash": terminal_hash,
            "completion_event": completion_event,
        }
