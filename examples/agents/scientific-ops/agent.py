"""scientific-ops agent: schedule lab instrument calibration via a WCP coordinator."""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from wcp_sdk.v2 import Agent

agent = Agent(name="lab-ops-agent", coordinator="ws://localhost:8000/wcp/ws")


def build_calibration_task(instrument_id: str, duration_minutes: int) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "schema_version": "wcp/0.2",
        "task_id": str(uuid.uuid4()),
        "posted_by": agent.did,
        "descriptor_type": "scheduled_presence",
        "descriptor_payload": {
            "instrument_id": instrument_id,
            "duration_minutes": duration_minutes,
            "calibration_protocol": "quarterly-NIST-traceable",
        },
        "constraints": {
            "time_window": {
                "earliest": now.isoformat(),
                "latest": (now + timedelta(hours=8)).isoformat(),
            },
            "worker_class_filter": {"allowed": ["human", "semi_autonomous"]},
        },
        "attestation_requirement": {
            "modes": ["cryptographic-presence", "sensor-witness"],
            "threshold": "M-of-N",
            "M": 2,
            "N": 2,
            "evidence_schema": [
                {"mode": "cryptographic-presence", "kinds": ["geofence_check_in_out"]},
                {"mode": "sensor-witness", "kinds": ["signed_sensor_recording"]},
            ],
        },
                "supervision": {"default": "autonomous"},
        "max_attestation_attempts": 1,
        "accounting_ref": "external-allocation",
        "x-subcontract-allowed": False,
    }


async def main() -> None:
    async with agent:
        task = build_calibration_task("spectrometer-12", 30)
        result = await agent.post_task(
            task,
            expiry=(datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
        )
        print(
            f"[agent] posted calibration task_id={result['task_id']} "
            f"({result['eligible_workers_count']} eligible workers)"
        )


if __name__ == "__main__":
    asyncio.run(main())
