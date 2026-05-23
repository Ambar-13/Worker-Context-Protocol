"""scientific-ops worker: a human technician calibrating lab instruments."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from wcp_sdk.types import AttestationMode
from wcp_sdk.v2 import Worker

worker = Worker(
    name="lab-technician-1",
    worker_class="human",
    coordinator="ws://localhost:8000/wcp/ws",
)


@worker.capability(
    descriptor_types=["scheduled_presence"],
    certifications=[
        {"issuer": "example-lab-cert-body", "id": "CALIB-INSTR-2026", "expires": "2027-12-31"}
    ],
    class_extension={"role": "calibration_technician", "shift_pool": "wet-lab"},
)
def declare() -> None:
    """Capability declaration."""


@worker.handle("scheduled_presence")
async def calibrate(task: dict) -> dict:
    payload = task.get("descriptor_payload", {})
    instrument_id = payload.get("instrument_id", "unknown")
    duration = payload.get("duration_minutes", 30)
    print(f"[worker] calibrating {instrument_id} for {duration} minutes")
    await asyncio.sleep(0.3)  # simulate work
    return {
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "instrument_id": instrument_id,
    }


@worker.attest(AttestationMode.CRYPTOGRAPHIC_PRESENCE)
async def attest_presence(claim_id: str, task: dict) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "kind": "geofence_check_in_out",
        "payload": {
            "check_in_at": now.isoformat(),
            "check_out_at": now.isoformat(),
            "region": {"polygon": [[0, 0], [10, 0], [10, 10], [0, 10]]},
        },
    }


@worker.attest(AttestationMode.SENSOR_WITNESS)
async def attest_instrument_log(claim_id: str, task: dict) -> dict:
    return {
        "kind": "signed_sensor_recording",
        "payload": {
            "recording_hash": "demo-instrument-log-hash",
            "duration_seconds": 1800,
        },
    }


if __name__ == "__main__":
    worker.run()
