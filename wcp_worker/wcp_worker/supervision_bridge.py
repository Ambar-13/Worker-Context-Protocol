"""WebRTC bridge for tasks/supervise handoff.

At v0.1 this is a thin wrapper around the WebRTC session URL returned by
the coordinator. The plugin opens the URL and forwards audio/video plus a
data-channel for state-snapshot signing. Production deployments wire the
data channel into the robot's safety stack to enforce takeover_authority.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from .identity import WorkerIdentity
from .rpc_client import RpcClient

log = logging.getLogger("wcp.supervision_bridge")


class SupervisionBridge:
    def __init__(self, identity: WorkerIdentity, rpc: RpcClient) -> None:
        self._identity = identity
        self._rpc = rpc

    async def request_supervisor(
        self,
        *,
        claim_id: str,
        handoff_reason: str,
        urgency: str,
        state_snapshot: dict[str, Any],
    ) -> dict[str, Any]:
        # Sign the state snapshot so the supervisor sees a tamper-evident
        # picture of the worker at handoff time.
        ts = datetime.now(timezone.utc).isoformat()
        signed = {
            "claim_id": claim_id,
            "state_snapshot": state_snapshot,
            "snapshot_at": ts,
        }
        signed["sig"] = self._identity.sign(signed)
        response = await self._rpc.call(
            "tasks/supervise",
            {
                "claim_id": claim_id,
                "handoff_reason": handoff_reason,
                "state_snapshot": signed,
                "urgency": urgency,
            },
        )
        return response

    async def open_webrtc_session(self, session_url: str) -> None:
        # INTEGRATION-GAP: integrate with an aiortc-based or vendor-supplied
        # WebRTC client. The v0.1 reference logs the URL and yields.
        log.info("supervision session ready at %s", session_url)
        await asyncio.sleep(0)
