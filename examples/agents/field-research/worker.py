"""field-research worker: a human researcher collecting environmental samples."""
from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from wcp_sdk.types import AttestationMode
from wcp_sdk.v2 import Worker

worker = Worker(name="researcher-12", worker_class="human",
                coordinator="ws://localhost:8000/wcp/ws")


@worker.capability(
    descriptor_types=["observe_and_report"],
    certifications=[{"issuer": "example-research-org", "id": "FIELD-OPS-L3", "expires": "2027-12-31"}],
    class_extension={"role": "environmental_field_researcher",
                     "carried_instruments": ["multiparameter_sonde", "GPS_handheld"]},
)
def declare() -> None: ...


@worker.handle("observe_and_report")
async def collect(task: dict) -> dict:
    sites = task.get("descriptor_payload", {}).get("sites", [])
    print(f"[worker] visiting {len(sites)} monitoring sites")
    await asyncio.sleep(0.3)
    return {"completed_at": datetime.now(timezone.utc).isoformat(), "sites_visited": len(sites)}


@worker.attest(AttestationMode.SENSOR_WITNESS)
async def attest_gps_and_sensor(claim_id: str, task: dict) -> dict:
    return {"kind": "signed_sensor_recording",
            "payload": {"recording_hash": "demo-sonde-recording-hash",
                        "duration_seconds": 600}}


if __name__ == "__main__":
    worker.run()
