"""disaster-response worker (drone scout). Other workers in this scenario are
ground vehicles and on-foot responders; they publish equivalent CapabilityDescriptors
with class autonomous_robot or human, and the verifier discriminates by (mode, kind)."""
from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from wcp_sdk.types import AttestationMode
from wcp_sdk.v2 import Worker

worker = Worker(name="aerial-scout-04", worker_class="autonomous_robot",
                coordinator="ws://localhost:8000/wcp/ws")


@worker.capability(
    descriptor_types=["observe_and_report", "transport"],
    certifications=[{"issuer": "example-aviation-authority", "id": "EMERGENCY-OPS-2026"}],
    class_extension={
        "kinematics": {"locomotion": "aerial", "max_speed_mps": 20.0, "footprint_m": [0.6, 0.6]},
        "payload": {"max_kg": 3, "max_dim_m": [0.3, 0.3, 0.1]},
        "environment": {"outdoor": True, "ip_rating": "IP55", "operating_temp_c": [-5, 45]},
    },
)
def declare() -> None: ...


@worker.handle("observe_and_report")
async def survey(task: dict) -> dict:
    zone = task.get("descriptor_payload", {}).get("scope", {})
    print(f"[worker] surveying zone {zone.get('zone_id')}")
    await asyncio.sleep(0.3)
    return {"surveyed_at": datetime.now(timezone.utc).isoformat()}


@worker.attest(AttestationMode.SENSOR_WITNESS)
async def attest_aerial_imagery(claim_id: str, task: dict) -> dict:
    return {"kind": "photo_with_exif",
            "payload": {"photo_hash": "demo-aerial-rgb-hash",
                        "exif": {"datetime": datetime.now(timezone.utc).isoformat(),
                                 "gps_lat": 1.290, "gps_lon": 103.851}}}


if __name__ == "__main__":
    worker.run()
