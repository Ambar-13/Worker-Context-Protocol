"""
High-level session classes for the worker and agent sides.

WorkerSession: build and publish CapabilityDescriptors, claim tasks, send
execute events, attest, supervise, abort.

AgentSession: post tasks, subscribe to capability updates.
"""
from __future__ import annotations

import asyncio
import uuid
from contextlib import AbstractAsyncContextManager
from datetime import datetime, timezone
from typing import Any, Optional

from .canonical import canonical_json_bytes, sha256_hex
from .identity import AgentIdentity, WorkerIdentity
from .rpc_client import RpcClient, WcpRpcError
from .types import (
    AttestationEvidence,
    AttestationMode,
    AttestationRequirement,
    CapabilityDescriptor,
    TaskDescriptor,
    VerifierDecision,
    WorkerClass,
)


class WorkerSession(AbstractAsyncContextManager["WorkerSession"]):
    """Worker-side session over a coordinator WebSocket."""

    def __init__(self, url: str, identity: WorkerIdentity) -> None:
        self.identity = identity
        self.rpc = RpcClient(url)
        self._heartbeat_tasks: dict[str, asyncio.Task[None]] = {}

    @classmethod
    async def connect(cls, url: str, identity: WorkerIdentity) -> "WorkerSession":
        s = cls(url, identity)
        await s.rpc.connect()
        return s

    async def __aenter__(self) -> "WorkerSession":
        await self.rpc.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        for t in self._heartbeat_tasks.values():
            t.cancel()
        await self.rpc.close()

    async def publish_capabilities(
        self, descriptor: CapabilityDescriptor
    ) -> dict[str, Any]:
        return await self.rpc.call(
            "capabilities/list",
            {"worker_id": self.identity.did, "capabilities": descriptor.to_dict()},
        )

    async def claim(
        self,
        *,
        task_id: str,
        eta: str,
        bid: Optional[str] = None,
    ) -> dict[str, Any]:
        payload_hash = sha256_hex(canonical_json_bytes({"task_id": task_id}))
        signed_at = datetime.now(timezone.utc).isoformat()
        canonical = {
            "task_id": task_id,
            "worker_id": self.identity.did,
            "eta": eta,
            "bid": bid,
            "payload_hash": payload_hash,
            "signed_at": signed_at,
        }
        acceptance = {
            "sig": self.identity.sign(canonical),
            "alg": "Ed25519",
            "payload_hash": payload_hash,
            "signed_at": signed_at,
        }
        return await self.rpc.call(
            "tasks/claim",
            {
                "task_id": task_id,
                "worker_id": self.identity.did,
                "eta": eta,
                "bid": bid,
                "acceptance_attestation": acceptance,
            },
        )

    async def execute_open(self, claim_id: str) -> dict[str, Any]:
        res = await self.rpc.call("tasks/execute", {"claim_id": claim_id})
        self._heartbeat_tasks[claim_id] = asyncio.create_task(
            self._heartbeat_loop(claim_id)
        )
        return res

    async def emit_event(
        self,
        claim_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        ts = datetime.now(timezone.utc).isoformat()
        sig = self.identity.sign(
            {
                "claim_id": claim_id,
                "event_type": event_type,
                "timestamp": ts,
                "payload": payload,
            }
        )
        return await self.rpc.call(
            "tasks/execute.event",
            {
                "claim_id": claim_id,
                "event_type": event_type,
                "timestamp": ts,
                "payload": payload,
                "sig": sig,
            },
        )

    async def _heartbeat_loop(self, claim_id: str) -> None:
        try:
            while True:
                try:
                    await self.emit_event(claim_id, "heartbeat", {"claim_id": claim_id})
                except WcpRpcError:
                    pass
                await asyncio.sleep(15.0)
        except asyncio.CancelledError:
            return

    async def attest(
        self,
        claim_id: str,
        evidence: list[AttestationEvidence],
        compensating_action: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "claim_id": claim_id,
            "attestations": [e.to_dict() for e in evidence],
        }
        if compensating_action is not None:
            params["compensating_action"] = compensating_action
        return await self.rpc.call("tasks/attest", params)

    async def supervise(
        self,
        claim_id: str,
        *,
        handoff_reason: str,
        state_snapshot: dict[str, Any],
        urgency: str,
    ) -> dict[str, Any]:
        return await self.rpc.call(
            "tasks/supervise",
            {
                "claim_id": claim_id,
                "handoff_reason": handoff_reason,
                "state_snapshot": state_snapshot,
                "urgency": urgency,
            },
        )

    async def abort(
        self,
        claim_id: str,
        *,
        reason: str,
        state_snapshot: dict[str, Any],
    ) -> dict[str, Any]:
        ht = self._heartbeat_tasks.pop(claim_id, None)
        if ht is not None:
            ht.cancel()
        return await self.rpc.call(
            "tasks/abort",
            {
                "claim_id": claim_id,
                "reason": reason,
                "state_snapshot": state_snapshot,
            },
        )

    def build_evidence(
        self,
        *,
        claim_id: str,
        mode: AttestationMode,
        kind: str,
        payload: dict[str, Any],
        collected_at: Optional[str] = None,
    ) -> AttestationEvidence:
        collected_at = collected_at or datetime.now(timezone.utc).isoformat()
        payload_hash = sha256_hex(canonical_json_bytes(payload))
        canonical = {
            "mode": mode.value,
            "kind": kind,
            "payload_hash": payload_hash,
            "worker_id": self.identity.did,
            "claim_id": claim_id,
            "collected_at": collected_at,
        }
        sig = self.identity.sign(canonical)
        return AttestationEvidence(
            mode=mode,
            kind=kind,
            payload=payload,
            payload_hash=payload_hash,
            sig=sig,
            worker_id=self.identity.did,
            claim_id=claim_id,
            collected_at=collected_at,
        )


class AgentSession(AbstractAsyncContextManager["AgentSession"]):
    """Agent-side session over a coordinator WebSocket."""

    def __init__(self, url: str, identity: AgentIdentity) -> None:
        self.identity = identity
        self.rpc = RpcClient(url)

    @classmethod
    async def connect(cls, url: str, identity: AgentIdentity) -> "AgentSession":
        s = cls(url, identity)
        await s.rpc.connect()
        return s

    async def __aenter__(self) -> "AgentSession":
        await self.rpc.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.rpc.close()

    async def post(
        self,
        task: TaskDescriptor,
        *,
        expiry: str,
        supervision: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "task": task.to_dict(),
            "expiry": expiry,
        }
        if supervision is not None:
            params["supervision"] = supervision
        return await self.rpc.call("tasks/post", params)

    async def subscribe(
        self,
        *,
        filter_dict: Optional[dict[str, Any]] = None,
        since_revision: Optional[int] = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"agent_did": self.identity.did}
        if filter_dict is not None:
            params["filter"] = filter_dict
        if since_revision is not None:
            params["since_revision"] = since_revision
        return await self.rpc.call("capabilities/subscribe", params)


def make_task_descriptor(
    *,
    posted_by: str,
    descriptor_type: str,
    descriptor_payload: dict[str, Any],
    attestation_modes: list[AttestationMode],
    attestation_kinds: dict[str, list[str]],
    M: int,
    N: int,
    worker_class_filter: Optional[list[WorkerClass]] = None,
    task_id: Optional[str] = None,
    time_window: Optional[dict[str, str]] = None,
    max_attestation_attempts: int = 1,
    marketplace_ref: Optional[str] = None,
) -> TaskDescriptor:
    """Ergonomic helper to construct a TaskDescriptor with sensible defaults.

    Settlement parameters are removed at v0.955; settlement is no longer a
    protocol concern. Pass ``marketplace_ref`` to correlate this task with
    an external settlement-layer record (a Stripe PaymentIntent ID, an SAP
    work-order number, a grant disbursement reference, etc.).
    """
    return TaskDescriptor(
        task_id=task_id or str(uuid.uuid4()),
        posted_by=posted_by,
        descriptor_type=descriptor_type,
        descriptor_payload=descriptor_payload,
        constraints={
            "time_window": time_window or {},
            "worker_class_filter": {
                "allowed": [c.value for c in (worker_class_filter or [WorkerClass.HUMAN])]
            },
        },
        attestation_requirement=AttestationRequirement(
            modes=attestation_modes,
            threshold="M-of-N",
            M=M,
            N=N,
            evidence_schema=[
                {"mode": m.value, "kinds": attestation_kinds.get(m.value, [])}
                for m in attestation_modes
            ],
        ),
        max_attestation_attempts=max_attestation_attempts,
        marketplace_ref=marketplace_ref,
    )
