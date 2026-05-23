"""Dispatches WCP task execution to robot-side adapters.

The executor receives a claimed task and the descriptor; routes by
`descriptor_type` to the right adapter. Emits signed execute-stream events
back to the coordinator through the RpcClient.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from .attestation_collector import AttestationCollector
from .identity import WorkerIdentity
from .nav_adapter import NavAdapter
from .rpc_client import RpcClient

log = logging.getLogger("wcp.task_executor")


class TaskExecutor:
    def __init__(
        self,
        identity: WorkerIdentity,
        rpc: RpcClient,
        nav: NavAdapter,
        collector: AttestationCollector,
    ) -> None:
        self._identity = identity
        self._rpc = rpc
        self._nav = nav
        self._collector = collector
        self._heartbeat_task: asyncio.Task[None] | None = None

    async def execute(
        self,
        *,
        claim_id: str,
        task: dict[str, Any],
    ) -> dict[str, Any]:
        await self._rpc.call("tasks/execute", {"claim_id": claim_id})
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop(claim_id))
        try:
            descriptor_type = task.get("descriptor_type")
            payload = task.get("descriptor_payload", {})
            if descriptor_type == "transport":
                evidence = await self._run_transport(claim_id, payload)
            elif descriptor_type == "scheduled_presence":
                evidence = await self._run_scheduled_presence(claim_id, payload)
            elif descriptor_type == "observe_and_report":
                evidence = await self._run_observe(claim_id, payload)
            else:
                raise NotImplementedError(
                    f"descriptor_type={descriptor_type!r} not implemented in v0.1 reference"
                )
            return await self._rpc.call(
                "tasks/attest",
                {"claim_id": claim_id, "attestations": evidence},
            )
        finally:
            if self._heartbeat_task is not None:
                self._heartbeat_task.cancel()

    async def _heartbeat_loop(self, claim_id: str) -> None:
        try:
            while True:
                ts = datetime.now(timezone.utc).isoformat()
                payload = {"claim_id": claim_id}
                sig = self._identity.sign(
                    {
                        "claim_id": claim_id,
                        "event_type": "heartbeat",
                        "timestamp": ts,
                        "payload": payload,
                    }
                )
                try:
                    await self._rpc.call(
                        "tasks/execute.event",
                        {
                            "claim_id": claim_id,
                            "event_type": "heartbeat",
                            "timestamp": ts,
                            "payload": payload,
                            "sig": sig,
                        },
                    )
                except Exception as exc:
                    log.warning("heartbeat send failed: %s", exc)
                await asyncio.sleep(15.0)
        except asyncio.CancelledError:
            return

    async def _run_transport(
        self, claim_id: str, payload: dict[str, Any]
    ) -> list[dict[str, Any]]:
        pickup = payload.get("pickup", {}).get("pose", [0.0, 0.0, 0.0])
        dropoff = payload.get("dropoff", {}).get("pose", [0.0, 0.0, 0.0])
        track: list[dict[str, Any]] = []
        # Pickup leg.
        await self._emit_event(claim_id, "picked_up", payload={"pose": pickup})
        track.append({"t": datetime.now(timezone.utc).isoformat(), "x": pickup[0], "y": pickup[1]})
        ok = await self._nav.navigate_to_pose(x=dropoff[0], y=dropoff[1])
        if not ok:
            await self._emit_event(claim_id, "nav_failed", payload={"target": dropoff})
        track.append({"t": datetime.now(timezone.utc).isoformat(), "x": dropoff[0], "y": dropoff[1]})
        await self._emit_event(claim_id, "arrived_at_dropoff", payload={"pose": dropoff})
        return [self._collector.indoor_pose_track(claim_id, track)]

    async def _run_scheduled_presence(
        self, claim_id: str, payload: dict[str, Any]
    ) -> list[dict[str, Any]]:
        duration_minutes = int(payload.get("duration_minutes", 1))
        check_in = datetime.now(timezone.utc)
        # In a real deployment, this is robot-driven; here we simulate.
        await asyncio.sleep(0.05)
        check_out = check_in
        try:
            from datetime import timedelta
            check_out = check_in + timedelta(minutes=duration_minutes)
        except Exception:
            pass
        region = payload.get("region", {"polygon": [[0, 0], [10, 0], [10, 10], [0, 10]]})
        return [
            self._collector.pose_bounded_presence_proof(
                claim_id,
                check_in_at=check_in,
                check_out_at=check_out,
                region=region,
            )
        ]

    async def _run_observe(
        self, claim_id: str, payload: dict[str, Any]
    ) -> list[dict[str, Any]]:
        return [
            self._collector.signed_sensor_recording(
                claim_id,
                recording_bytes=b"stub-recording",
                duration_seconds=int(payload.get("duration_seconds", 30)),
            )
        ]

    async def _emit_event(
        self,
        claim_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        ts = datetime.now(timezone.utc).isoformat()
        sig = self._identity.sign(
            {
                "claim_id": claim_id,
                "event_type": event_type,
                "timestamp": ts,
                "payload": payload,
            }
        )
        await self._rpc.call(
            "tasks/execute.event",
            {
                "claim_id": claim_id,
                "event_type": event_type,
                "timestamp": ts,
                "payload": payload,
                "sig": sig,
            },
        )
