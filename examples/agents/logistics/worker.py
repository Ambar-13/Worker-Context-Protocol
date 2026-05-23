"""logistics worker: an AMR (or human forklift operator with same protocol)."""
from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from wcp_sdk.types import AttestationMode
from wcp_sdk.v2 import Worker

worker = Worker(name="amr-fleet-7", worker_class="autonomous_robot",
                coordinator="ws://localhost:8000/wcp/ws")


@worker.capability(
    descriptor_types=["transport"],
    certifications=[{"issuer": "example-warehouse-cert", "id": "AMR-LICENSE-2026"}],
    class_extension={
        "kinematics": {"locomotion": "wheeled", "max_speed_mps": 1.5, "footprint_m": [1.2, 0.8]},
        "payload": {"max_kg": 800, "max_dim_m": [1.2, 0.8, 1.5]},
        "end_effectors": [{"class": "fork", "rated_for": ["pallet_eur1", "pallet_us48x40"]}],
    },
)
def declare() -> None: ...


@worker.handle("transport")
async def move_pallet(task: dict) -> dict:
    p = task.get("descriptor_payload", {})
    print(f"[worker] moving pallet {p.get('payload_description')} "
          f"from {p.get('pickup')} to {p.get('dropoff')}")
    await asyncio.sleep(0.4)
    return {"delivered_at": datetime.now(timezone.utc).isoformat()}


@worker.attest(AttestationMode.SENSOR_WITNESS)
async def attest_pose_and_weight(claim_id: str, task: dict) -> dict:
    return {"kind": "indoor_pose_track",
            "payload": {"track": [
                {"t": "2026-06-01T10:00:00Z", "x": 0.0, "y": 0.0},
                {"t": "2026-06-01T10:02:00Z", "x": 12.0, "y": 5.0},
            ]}}


@worker.attest(AttestationMode.THIRD_PARTY_WITNESS)
async def attest_bay_beacon(claim_id: str, task: dict) -> dict:
    return {"kind": "iot_beacon_proximity",
            "payload": {"beacon_id": "staging-bay-3", "rssi": -42,
                        "observed_at": datetime.now(timezone.utc).isoformat()}}


if __name__ == "__main__":
    worker.run()
