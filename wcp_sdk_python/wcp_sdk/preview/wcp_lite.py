"""
RFC 0029 preview: WCP-Lite for Intermittent Connectivity.

Provides BufferedAuditChain for workers that operate under predictable or
unpredictable disconnect windows (subsea ROVs, basement-tunnel AMRs,
deployed quadrupeds in metal-clad sites, remote-field-research stations).

Pattern: worker buffers signed audit entries locally during disconnect;
coordinator accepts the batch on reconnect with hash-chain integrity
verification across batch boundaries.

This preview is the worker-side runtime. The coordinator-side batch verifier
ships as part of the v1.1 reference coordinator; this preview can be unit
tested with a stub coordinator client.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Iterable, Optional

from . import emit_preview_warning


CONNECTIVITY_CONTINUOUS = "continuous"
CONNECTIVITY_INTERMITTENT = "intermittent"
CONNECTIVITY_UNPREDICTABLE = "unpredictable"


@dataclass
class AuditEntry:
    """Single audit chain entry buffered locally during disconnect."""

    entry_id: str
    task_id: str
    claim_id: Optional[str]
    timestamp: str  # RFC 3339; worker-claimed submitted_at
    signer_did: str
    payload: dict
    previous_entry_hash: Optional[str]
    entry_hash: str
    signature: str


@dataclass
class BufferOverflowError(Exception):
    """Raised when the local buffer exceeds the declared capacity."""

    capacity: int
    attempted_count: int

    def __str__(self) -> str:
        return (
            f"WCP-Lite buffer overflow: capacity {self.capacity}, "
            f"attempted {self.attempted_count}"
        )


class BufferedAuditChain:
    """Worker-side append-only buffered audit chain.

    Use:
        chain = BufferedAuditChain(
            worker_did="did:wcp:zABC...",
            capacity=10_000,
        )
        chain.append(task_id, claim_id, signer_did, payload, signature_fn)
        ...
        # On reconnect:
        await chain.replay_on_reconnect(coordinator_client)
    """

    def __init__(
        self,
        *,
        worker_did: str,
        capacity: int = 10_000,
    ) -> None:
        emit_preview_warning(29, "wcp_lite")
        self.worker_did = worker_did
        self.capacity = capacity
        self._entries: list[AuditEntry] = []
        self._last_hash: Optional[str] = None

    def __len__(self) -> int:
        return len(self._entries)

    @property
    def is_full(self) -> bool:
        return len(self._entries) >= self.capacity

    def append(
        self,
        *,
        entry_id: str,
        task_id: str,
        claim_id: Optional[str],
        signer_did: str,
        payload: dict,
        signature: str,
        timestamp: Optional[str] = None,
    ) -> AuditEntry:
        """Append a signed audit entry to the local buffer.

        Computes entry_hash = sha256(canonical_json({...entry contents...}))
        and links to the previous entry's hash. Raises BufferOverflowError if
        the buffer is at capacity.
        """
        if self.is_full:
            raise BufferOverflowError(
                capacity=self.capacity, attempted_count=len(self._entries) + 1
            )
        ts = timestamp or datetime.now(timezone.utc).isoformat()
        entry_body = {
            "entry_id": entry_id,
            "task_id": task_id,
            "claim_id": claim_id,
            "timestamp": ts,
            "signer_did": signer_did,
            "payload": payload,
            "previous_entry_hash": self._last_hash,
        }
        canonical = json.dumps(entry_body, sort_keys=True, separators=(",", ":"))
        entry_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        entry = AuditEntry(
            entry_id=entry_id,
            task_id=task_id,
            claim_id=claim_id,
            timestamp=ts,
            signer_did=signer_did,
            payload=payload,
            previous_entry_hash=self._last_hash,
            entry_hash=entry_hash,
            signature=signature,
        )
        self._entries.append(entry)
        self._last_hash = entry_hash
        return entry

    def verify_chain_integrity(self) -> bool:
        """Verify that the buffered chain links cleanly.

        Recomputes each entry's hash and confirms previous_entry_hash links.
        Returns True if the chain is intact, False otherwise.
        """
        emit_preview_warning(29, "wcp_lite")
        prev_hash: Optional[str] = None
        for entry in self._entries:
            entry_body = {
                "entry_id": entry.entry_id,
                "task_id": entry.task_id,
                "claim_id": entry.claim_id,
                "timestamp": entry.timestamp,
                "signer_did": entry.signer_did,
                "payload": entry.payload,
                "previous_entry_hash": entry.previous_entry_hash,
            }
            canonical = json.dumps(entry_body, sort_keys=True, separators=(",", ":"))
            expected = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            if entry.entry_hash != expected:
                return False
            if entry.previous_entry_hash != prev_hash:
                return False
            prev_hash = entry.entry_hash
        return True

    def entries_for_replay(self) -> Iterable[AuditEntry]:
        """Iterate buffered entries in append order for batch replay."""
        return iter(self._entries)

    def clear(self) -> None:
        """Clear the buffer after successful replay."""
        self._entries.clear()
        self._last_hash = None

    async def replay_on_reconnect(
        self, submit_fn: Callable[[list[AuditEntry]], Awaitable[bool]]
    ) -> bool:
        """Submit accumulated entries to the coordinator on reconnect.

        `submit_fn` is an async callable accepting the batch of entries.
        Returns True if the coordinator accepted the batch, False otherwise.
        On success, clears the buffer.
        """
        emit_preview_warning(29, "wcp_lite")
        if not self._entries:
            return True
        if not self.verify_chain_integrity():
            return False
        batch = list(self._entries)
        accepted = await submit_fn(batch)
        if accepted:
            self.clear()
        return accepted


def build_intermittent_capability_extension(
    *,
    max_offline_duration_seconds: int,
    expected_disconnect_pattern: str = "predictable",
    buffer_capacity_audit_entries: int = 10_000,
) -> dict[str, Any]:
    """Helper to build the class_extension block declaring WCP-Lite profile.

    Embed the return value as CapabilityDescriptor.class_extension when
    declaring an intermittent-connectivity worker. See RFC 0029 section
    "Capability declaration".
    """
    emit_preview_warning(29, "wcp_lite")
    if expected_disconnect_pattern not in ("predictable", "unpredictable"):
        raise ValueError(
            f"expected_disconnect_pattern must be 'predictable' or 'unpredictable', "
            f"got {expected_disconnect_pattern!r}"
        )
    if max_offline_duration_seconds <= 0:
        raise ValueError(
            f"max_offline_duration_seconds must be positive, got {max_offline_duration_seconds}"
        )
    return {
        "connectivity_profile": CONNECTIVITY_INTERMITTENT,
        "max_offline_duration_seconds": max_offline_duration_seconds,
        "expected_disconnect_pattern": expected_disconnect_pattern,
        "buffer_capacity_audit_entries": buffer_capacity_audit_entries,
    }


def build_task_constraint_for_intermittent_executor(
    *,
    accepts_intermittent_executor: bool = True,
    max_acceptable_offline_seconds: Optional[int] = None,
) -> dict[str, Any]:
    """Helper to build the constraints block for a task that accepts WCP-Lite workers.

    Embed in TaskDescriptor.constraints. See RFC 0029 section "Tasks/post flow".
    """
    emit_preview_warning(29, "wcp_lite")
    out: dict[str, Any] = {
        "accepts_intermittent_executor": accepts_intermittent_executor,
    }
    if max_acceptable_offline_seconds is not None:
        if max_acceptable_offline_seconds <= 0:
            raise ValueError(
                "max_acceptable_offline_seconds must be positive when set"
            )
        out["max_acceptable_offline_seconds"] = max_acceptable_offline_seconds
    return out
