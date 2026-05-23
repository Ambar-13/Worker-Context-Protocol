"""disaster-response agent: dispatch survey tasks across mixed worker classes."""
from __future__ import annotations
import asyncio, uuid
from datetime import datetime, timedelta, timezone
from wcp_sdk.v2 import Agent

agent = Agent(name="incident-commander-agent", coordinator="ws://localhost:8000/wcp/ws")


def build_zone_survey(zone_id: str, polygon: list[list[float]]) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "schema_version": "wcp/0.2",
        "task_id": str(uuid.uuid4()),
        "posted_by": agent.did,
        "descriptor_type": "observe_and_report",
        "descriptor_payload": {
            "scope": {"zone_id": zone_id, "polygon": polygon},
            "sensor_classes": ["rgb_camera", "thermal_ir"],
            "sampling": "tile sweep at 25m altitude; closeup over structural damage",
            "deliverable_schema": "wcp/observation/1.0-rc1",
            "cross_attest_min_witnesses": 3,
        },
        "constraints": {
            "time_window": {"earliest": now.isoformat(),
                            "latest": (now + timedelta(hours=4)).isoformat()},
            "worker_class_filter": {"allowed": ["autonomous_robot", "teleoperated_robot", "human"]},
        },
        "attestation_requirement": {
            "modes": ["sensor-witness"],
            "threshold": "M-of-N", "M": 3, "N": 5,
            "evidence_schema": [
                {"mode": "sensor-witness", "kinds": ["photo_with_exif", "signed_sensor_recording"]},
            ],
        },
                "supervision": {"default": "co_pilot"},
        "max_attestation_attempts": 1,
        "accounting_ref": "external-allocation",
        "x-subcontract-allowed": False,
    }


async def main() -> None:
    async with agent:
        task = build_zone_survey("zone-c-northeast",
                                 [[0,0],[100,0],[100,80],[0,80]])
        res = await agent.post_task(
            task,
            expiry=(datetime.now(timezone.utc) + timedelta(hours=4)).isoformat(),
        )
        print(f"[agent] posted zone survey task_id={res['task_id']} "
              f"({res['eligible_workers_count']} eligible workers)")


if __name__ == "__main__":
    asyncio.run(main())
