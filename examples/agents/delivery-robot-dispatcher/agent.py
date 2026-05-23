"""delivery_robot_dispatcher: the robot-as-agent reference deployment.

Domain: industrial logistics inside a manufacturing facility.

This script does NOT play the role of the AMR's onboard agent itself; that
runs inside the AMR worker (see worker.py, where a RobotAgent is instantiated
from inside the execute handler and posts the place_on_shelf follow-up).

Instead, this script plays the role of the upstream planner agent: it posts
the initial `transport` task that the AMR claims. Once the AMR has attested
the transport and the AMR's onboard RobotAgent has posted the follow-up
`place_on_shelf` task, this script watches both tasks complete.

Reference: spec/0.95.md Sections 2-6.
Pattern doc: docs/patterns/robot-as-agent.md.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from wcp_sdk.v2 import Agent

agent = Agent(
    name="manufacturing-line-planner",
    coordinator="ws://localhost:8000/wcp/ws",
)


def build_transport_task(
    *,
    component_id: str,
    source: str,
    destination_workstation: str,
) -> dict:
    """Move a component from staging to a workstation. The AMR will then
    post a follow-up place_on_shelf task that a stationary manipulator
    claims; the runbook for that follow-up lives inside the AMR worker."""
    now = datetime.now(timezone.utc)
    return {
        "schema_version": "wcp/0.2",
        "task_id": str(uuid.uuid4()),
        "posted_by": agent.did,
        "descriptor_type": "transport",
        "descriptor_payload": {
            "component_id": component_id,
            "source": source,
            "destination": destination_workstation,
            "handoff_protocol": "place_on_shelf_via_continuation",
        },
        "constraints": {
            "time_window": {
                "earliest": now.isoformat(),
                "latest": (now + timedelta(hours=1)).isoformat(),
            },
            "worker_class_filter": {"allowed": ["autonomous_robot"]},
        },
        "attestation_requirement": {
            "modes": ["sensor-witness", "third-party-witness"],
            "threshold": "M-of-N",
            "M": 2,
            "N": 2,
            "evidence_schema": [
                {
                    "mode": "sensor-witness",
                    "kinds": ["indoor_pose_track", "weight_delta"],
                },
                {
                    "mode": "third-party-witness",
                    "kinds": ["iot_beacon_proximity"],
                },
            ],
        },
                "supervision": {"default": "autonomous"},
    }


async def main() -> None:
    async with agent:
        task = build_transport_task(
            component_id="component-bb-1042",
            source="staging-bay-2",
            destination_workstation="workstation-7",
        )
        result = await agent.post_task(
            task,
            expiry=(
                datetime.now(timezone.utc) + timedelta(hours=2)
            ).isoformat(),
        )
        print(
            f"[planner] posted transport task_id={result.get('task_id')} "
            f"({result.get('eligible_workers_count', 0)} eligible workers)"
        )
        print(
            "[planner] AMR worker will post a place_on_shelf follow-up "
            "via continuation_of after the transport attests; watch the "
            "coordinator's audit chain for the linked entries."
        )


if __name__ == "__main__":
    asyncio.run(main())
