"""
Vendor robot bridge: skeleton bridge template.

This is a starting point for writing a WCP adapter for a robot platform
not covered by the other adapters in this directory. Replace the
TODO-marked sections with your vendor's actual SDK calls.

The pattern:

1. Define a `VendorRobotClient` Protocol that wraps the vendor's SDK in
   an async interface (typically: connect, get_info, execute_motion,
   capture_image, get_pose_stream, etc.)
2. Map each WCP descriptor_type the bridge supports to one or more
   vendor SDK calls in `_wire_handlers`
3. Translate vendor telemetry into a WCP evidence kind in the
   `@worker.attest` handlers
4. Choose a `connectivity_profile` that matches deployment reality

Once you have a working bridge, consider submitting it back to the
WCP repository as a new adapter under examples/adapters/.
"""
from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional, Protocol

from wcp_sdk.types import AttestationMode
from wcp_sdk.v2 import Worker

from . import capability as cap_mod


class VendorRobotClient(Protocol):
    """Replace this Protocol with your vendor's SDK surface.

    The methods below are illustrative; rename/add/remove to match the
    actual API. Keep the surface narrow so the bridge can be unit-tested
    with a fake.
    """

    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...
    async def get_info(self) -> dict[str, Any]: ...
    async def execute_motion(
        self, motion_id: str, params: dict[str, Any]
    ) -> dict[str, Any]: ...
    async def get_telemetry_stream(
        self,
    ) -> "asyncio.Queue[dict[str, Any]]": ...


@dataclass
class VendorBridgeConfig:
    coordinator_url: str = "ws://localhost:8000/wcp/ws"
    worker_did: str = "did:wcp:example-vendor-robot-001"
    coordinator_did: str = "did:wcp:example-coordinator"
    adapter_signer_key_id: str = "k1"
    adapter_pubkey_multibase: str = "z6Mk-EXAMPLE-vendor-pubkey"
    descriptor_types: tuple[str, ...] = ("vendor_generic_task",)
    # TODO: list the evidence kinds your bridge produces; register them
    # with the coordinator's RFC 0003 evidence kind registry first.
    attestation_kinds: tuple[str, ...] = ("vendor_motion_telemetry",)


@dataclass
class _TaskRun:
    claim_id: str
    descriptor_type: str
    started_at: str = ""
    finished_at: str = ""
    result: Optional[dict[str, Any]] = None
    telemetry: list[dict[str, Any]] = field(default_factory=list)


class VendorRobotBridge:
    """Skeleton WCP worker. Customize the handlers below."""

    def __init__(
        self,
        config: VendorBridgeConfig,
        client: VendorRobotClient,
    ) -> None:
        self.cfg = config
        self.client = client
        self.worker = Worker(
            name="vendor-robot-bridge",
            worker_class="autonomous_robot",  # TODO if different
            coordinator=config.coordinator_url,
        )
        self._runs: dict[str, _TaskRun] = {}
        self._info: dict[str, Any] = {}
        self._wire_handlers()

    def _wire_handlers(self) -> None:
        worker = self.worker
        bridge = self

        @worker.capability(
            descriptor_types=list(self.cfg.descriptor_types),
            class_extension=cap_mod.vendor_info_to_class_extension({}),
        )
        def declare() -> None:
            return None

        for dt in self.cfg.descriptor_types:
            @worker.handle(dt)  # type: ignore[misc]
            async def execute(task: dict, _dt=dt) -> dict:
                # TODO: choose the vendor API call appropriate to this
                # descriptor_type. The mapping is per-vendor.
                claim_id = task["claim_id"]
                started = datetime.now(timezone.utc).isoformat()
                run = _TaskRun(
                    claim_id=claim_id,
                    descriptor_type=_dt,
                    started_at=started,
                )
                bridge._runs[claim_id] = run

                # Stream telemetry during execution
                tel_q = await bridge.client.get_telemetry_stream()
                tel_task = asyncio.create_task(
                    bridge._collect_telemetry(run, tel_q)
                )
                try:
                    result = await bridge.client.execute_motion(
                        motion_id=_dt,
                        params=task.get("descriptor_payload", {}),
                    )
                finally:
                    tel_task.cancel()
                run.result = result
                run.finished_at = datetime.now(timezone.utc).isoformat()
                return {
                    "started_at": started,
                    "finished_at": run.finished_at,
                    "result_summary": result.get("status", "ok"),
                }

        @worker.attest(AttestationMode.SENSOR_WITNESS)
        async def attest(claim_id: str, task: dict) -> dict:
            run = bridge._runs.get(claim_id)
            if run is None:
                return {
                    "kind": self.cfg.attestation_kinds[0],
                    "payload": {"telemetry": []},
                }
            # TODO: shape the evidence payload per the registered
            # evidence kind. The default below is a placeholder.
            return {
                "kind": self.cfg.attestation_kinds[0],
                "payload": {
                    "started_at": run.started_at,
                    "finished_at": run.finished_at,
                    "telemetry_samples": len(run.telemetry),
                    "telemetry": run.telemetry,
                    "result": run.result,
                },
            }

    async def _collect_telemetry(
        self, run: _TaskRun, q: "asyncio.Queue[dict[str, Any]]"
    ) -> None:
        try:
            while True:
                msg = await q.get()
                run.telemetry.append(
                    {
                        "t": datetime.now(timezone.utc).isoformat(),
                        "msg": msg,
                    }
                )
        except asyncio.CancelledError:
            return

    async def run(self) -> None:
        await self.client.connect()
        try:
            self._info = await self.client.get_info()
            await asyncio.to_thread(self.worker.run)
        finally:
            await self.client.disconnect()


def main() -> None:
    cfg = VendorBridgeConfig(
        coordinator_url=os.environ.get(
            "WCP_COORDINATOR", "ws://localhost:8000/wcp/ws"
        ),
    )
    raise SystemExit(
        "This is a template. Implement VendorRobotClient against your "
        "vendor's SDK, then instantiate "
        "VendorRobotBridge(cfg, client).run()."
    )


if __name__ == "__main__":
    main()
