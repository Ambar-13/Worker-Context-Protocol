"""
MAVLink-to-WCP bridge.

Runs as a WCP worker that holds a MAVLink connection (UDP/serial/TCP) to a
single vehicle. The bridge:

1. Connects to the vehicle's MAVLink endpoint
2. Reads HEARTBEAT/SYS_STATUS/GLOBAL_POSITION_INT to detect liveness and
   build the capability declaration
3. Subscribes to coordinator tasks via the WCP SDK
4. On a claimed aerial-inspection / aerial-survey task, translates the
   descriptor into a MAVLink mission (MISSION_ITEM_INT items)
5. Uploads the mission, arms, and starts AUTO mode
6. Streams pose into a `geo_track` evidence buffer
7. On mission complete, signs and submits attestation evidence

The full MAVLink interaction requires either pymavlink or mavsdk and a
live vehicle (or PX4 SITL). This file shows the WCP-side surface; the
south-bound calls are isolated behind a `MAVLinkConnection` protocol so
they can be substituted for a fake during unit tests.
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


class MAVLinkConnection(Protocol):
    """Abstract surface for south-bound MAVLink I/O.

    A real implementation backs this with pymavlink or mavsdk;
    `FakeMAVLink` in `tests/` substitutes a scripted vehicle.
    """

    async def wait_for_heartbeat(self, timeout_s: float = 10.0) -> dict[str, Any]: ...

    async def upload_mission(self, items: list[dict[str, Any]]) -> None: ...

    async def arm(self) -> None: ...

    async def start_auto(self) -> None: ...

    async def stream_global_position(self) -> "asyncio.Queue[dict[str, Any]]": ...

    async def wait_for_mission_complete(self, timeout_s: float = 1800.0) -> None: ...

    async def land(self) -> None: ...


@dataclass
class MAVLinkBridgeConfig:
    coordinator_url: str = "ws://localhost:8000/wcp/ws"
    mavlink_endpoint: str = "udp://:14540"  # PX4 SITL default
    worker_did: str = "did:wcp:example-mavlink-drone-001"
    coordinator_did: str = "did:wcp:example-coordinator"
    adapter_signer_key_id: str = "k1"
    adapter_pubkey_multibase: str = "z6Mk-EXAMPLE-mavlink-pubkey"
    mav_type: str = "quadrotor"


@dataclass
class _GeoTrackBuffer:
    """Accumulates GLOBAL_POSITION_INT samples for a single claim."""

    claim_id: str
    samples: list[dict[str, Any]] = field(default_factory=list)

    def append(self, msg: dict[str, Any]) -> None:
        self.samples.append(
            {
                "t": datetime.now(timezone.utc).isoformat(),
                "lat_deg": msg["lat"] / 1e7,
                "lon_deg": msg["lon"] / 1e7,
                "alt_m_msl": msg["alt"] / 1000.0,
                "vx_mps": msg["vx"] / 100.0,
                "vy_mps": msg["vy"] / 100.0,
                "vz_mps": msg["vz"] / 100.0,
                "hdg_deg": msg["hdg"] / 100.0,
            }
        )

    def to_evidence_payload(self) -> dict[str, Any]:
        return {
            "kind": "geo_track",
            "payload": {
                "sample_count": len(self.samples),
                "track": self.samples,
            },
        }


def descriptor_to_mavlink_mission(
    descriptor_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    """Translate a WCP aerial-* descriptor_payload into MAVLink mission items.

    Expected descriptor_payload shape (per the example aerial schemas
    in `docs/concepts/`):

        {
            "waypoints": [
                {"lat_deg": 47.397, "lon_deg": 8.545, "alt_m_agl": 50},
                ...
            ],
            "takeoff_alt_m_agl": 20,
            "landing_lat_lon": [47.397, 8.545]
        }

    Returns a list of MAVLink MISSION_ITEM_INT dicts with command numbers:
        22 = NAV_TAKEOFF
        16 = NAV_WAYPOINT
        21 = NAV_LAND
    """
    items: list[dict[str, Any]] = []
    seq = 0
    items.append(
        {
            "seq": seq,
            "frame": 3,  # GLOBAL_RELATIVE_ALT
            "command": 22,  # NAV_TAKEOFF
            "current": 1,
            "autocontinue": 1,
            "x": 0, "y": 0,
            "z": descriptor_payload.get("takeoff_alt_m_agl", 20),
        }
    )
    seq += 1
    for wp in descriptor_payload.get("waypoints", []):
        items.append(
            {
                "seq": seq,
                "frame": 3,
                "command": 16,  # NAV_WAYPOINT
                "current": 0,
                "autocontinue": 1,
                "x": int(wp["lat_deg"] * 1e7),
                "y": int(wp["lon_deg"] * 1e7),
                "z": wp["alt_m_agl"],
            }
        )
        seq += 1
    land_ll = descriptor_payload.get("landing_lat_lon")
    if land_ll:
        items.append(
            {
                "seq": seq,
                "frame": 3,
                "command": 21,  # NAV_LAND
                "current": 0,
                "autocontinue": 1,
                "x": int(land_ll[0] * 1e7),
                "y": int(land_ll[1] * 1e7),
                "z": 0,
            }
        )
    return items


class MAVLinkBridge:
    """The WCP worker process that bridges to a single MAVLink vehicle."""

    def __init__(
        self,
        config: MAVLinkBridgeConfig,
        mavlink: MAVLinkConnection,
    ) -> None:
        self.cfg = config
        self.mav = mavlink
        self.worker = Worker(
            name="mavlink-bridge",
            worker_class="autonomous_robot",
            coordinator=config.coordinator_url,
        )
        self._geo_buffers: dict[str, _GeoTrackBuffer] = {}
        self._wire_handlers()

    def _wire_handlers(self) -> None:
        worker = self.worker
        bridge = self

        @worker.capability(
            descriptor_types=[
                "aerial_inspection",
                "aerial_survey",
                "aerial_delivery_lite",
            ],
            class_extension=cap_mod.mavlink_type_to_wcp_class_extension(
                mav_type=self.cfg.mav_type,
                battery_capacity_mah=5200,
                max_payload_kg=2.0,
                max_endurance_minutes=28.0,
                max_range_km=8.0,
                sensors=["rgb_camera_4k", "thermal_640", "gnss_l1l5"],
            ),
        )
        def declare() -> None:
            return None

        @worker.handle("aerial_inspection")
        @worker.handle("aerial_survey")
        async def fly(task: dict) -> dict:
            claim_id = task["claim_id"]
            payload = task.get("descriptor_payload", {})
            mission = descriptor_to_mavlink_mission(payload)
            buf = _GeoTrackBuffer(claim_id=claim_id)
            bridge._geo_buffers[claim_id] = buf

            await bridge.mav.upload_mission(mission)
            await bridge.mav.arm()
            await bridge.mav.start_auto()

            pos_q = await bridge.mav.stream_global_position()
            mission_task = asyncio.create_task(
                bridge.mav.wait_for_mission_complete()
            )
            while not mission_task.done():
                try:
                    msg = await asyncio.wait_for(pos_q.get(), timeout=0.5)
                    buf.append(msg)
                except asyncio.TimeoutError:
                    continue
            await mission_task
            return {
                "mission_completed_at": datetime.now(timezone.utc).isoformat(),
                "sample_count": len(buf.samples),
            }

        @worker.attest(AttestationMode.SENSOR_WITNESS)
        async def attest_geo_track(claim_id: str, task: dict) -> dict:
            buf = bridge._geo_buffers.get(claim_id)
            if buf is None:
                return {"kind": "geo_track", "payload": {"track": []}}
            return buf.to_evidence_payload()

    def run(self) -> None:
        self.worker.run()


def main() -> None:
    cfg = MAVLinkBridgeConfig(
        coordinator_url=os.environ.get(
            "WCP_COORDINATOR", "ws://localhost:8000/wcp/ws"
        ),
        mavlink_endpoint=os.environ.get("MAVLINK_ENDPOINT", "udp://:14540"),
    )
    # Production: from .pymavlink_impl import PymavlinkConnection
    # mav = PymavlinkConnection(cfg.mavlink_endpoint)
    # The default import is deliberately omitted so the WCP-side bridge
    # can be unit-tested without pymavlink installed.
    raise SystemExit(
        "Wire a MAVLinkConnection implementation (e.g., pymavlink) and "
        "instantiate MAVLinkBridge(cfg, mav).run(). See README.md."
    )


if __name__ == "__main__":
    main()
