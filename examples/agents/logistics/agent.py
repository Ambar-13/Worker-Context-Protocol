"""logistics agent: dispatch a pallet move to whichever worker class claims."""
from __future__ import annotations
import asyncio, uuid
from datetime import datetime, timedelta, timezone
from wcp_sdk.v2 import Agent

agent = Agent(name="dock-orchestrator", coordinator="ws://localhost:8000/wcp/ws")


def build_pallet_move(payload_desc: str, pickup: str, dropoff: str) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "schema_version": "wcp/0.2",
        "task_id": str(uuid.uuid4()),
        "posted_by": agent.did,
        "descriptor_type": "transport",
        "descriptor_payload": {
            "pickup": pickup, "dropoff": dropoff,
            "payload_description": payload_desc,
            "handoff_protocol": "beacon_proximity_then_weight_zero",
        },
        "constraints": {
            "time_window": {"earliest": now.isoformat(),
                            "latest": (now + timedelta(hours=2)).isoformat()},
            "worker_class_filter": {"allowed": ["autonomous_robot", "human"]},
        },
        "attestation_requirement": {
            "modes": ["sensor-witness", "third-party-witness"],
            "threshold": "M-of-N", "M": 2, "N": 2,
            "evidence_schema": [
                {"mode": "sensor-witness", "kinds": ["indoor_pose_track", "weight_delta"]},
                {"mode": "third-party-witness", "kinds": ["iot_beacon_proximity"]},
            ],
        },
                "supervision": {"default": "autonomous"},
        "max_attestation_attempts": 1,
        "accounting_ref": "external-allocation",
        "x-subcontract-allowed": False,
    }


async def main() -> None:
    async with agent:
        task = build_pallet_move("pallet-eur1 of widgets, ~620kg",
                                 "bay-recv-3", "stage-d-row-14")
        res = await agent.post_task(
            task,
            expiry=(datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
        )
        print(f"[agent] posted pallet-move task_id={res['task_id']} "
              f"({res['eligible_workers_count']} eligible workers)")


if __name__ == "__main__":
    asyncio.run(main())
