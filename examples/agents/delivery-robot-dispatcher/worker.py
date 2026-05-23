"""delivery_robot_dispatcher: the AMR worker AND its onboard RobotAgent.

This script declares the AMR's transport capability and, on the AMR's
`tasks/execute` handler, instantiates a RobotAgent and uses
`post_continuation` to publish a follow-up `place_on_shelf` task that a
stationary manipulator (a different worker class) will claim.

The follow-up task carries a `continuation_of` block that names the
transport task's claim_id and the evidence kinds the manipulator's
verifier may read for context.

Reference: spec/1.0-rc5.md and docs/patterns/robot-as-agent.md.

Note: a second worker process for the stationary manipulator runs as
`manipulator_worker.py` in this directory. The two workers connect to the
same local coordinator; the AMR posts the follow-up; the manipulator
claims and attests it.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from wcp_sdk.types import AttestationMode
from wcp_sdk.v2 import RobotAgent, Worker

# --- The AMR worker itself --------------------------------------------------

worker = Worker(
    name="amr-line-7",
    worker_class="autonomous_robot",
    coordinator="ws://localhost:8000/wcp/ws",
)


@worker.capability(
    descriptor_types=["transport"],
    certifications=[
        {"issuer": "facility-amr-cert", "id": "AMR-LICENSE-LINE-7-2026"}
    ],
    class_extension={
        "kinematics": {
            "locomotion": "wheeled",
            "max_speed_mps": 1.5,
            "footprint_m": [1.2, 0.8],
        },
        "payload": {"max_kg": 800, "max_dim_m": [1.2, 0.8, 1.5]},
        "end_effectors": [
            {"class": "fork", "rated_for": ["component_tray", "pallet_eur1"]}
        ],
        # The presence of an onboard RobotAgent is also a capability.
        "onboard_agent": {
            "agent_class": "embodied_agent",
            "post_continuation_supported": True,
        },
    },
)
def declare() -> None:
    return None


@worker.handle("transport")
async def move_component(task: dict) -> dict:
    """Execute the transport. After the transport attests, the AMR's
    onboard RobotAgent posts a place_on_shelf follow-up task."""
    payload = task.get("descriptor_payload", {}) or {}
    claim_id = task.get("claim_id", "")
    print(
        f"[amr] moving component {payload.get('component_id')} "
        f"from {payload.get('source')} to {payload.get('destination')} "
        f"(claim_id={claim_id})"
    )
    # Simulate execution
    await asyncio.sleep(0.4)
    result = {
        "delivered_at": datetime.now(timezone.utc).isoformat(),
        "destination": payload.get("destination"),
    }
    # Post the follow-up. The execute handler returns AFTER posting the
    # continuation so the transport attestation references can be set up
    # cleanly. A production AMR would tear down the post-continuation
    # client after each handoff.
    await _post_place_on_shelf_continuation(
        prior_claim_id=claim_id,
        destination=payload.get("destination", "unknown-workstation"),
        component_id=payload.get("component_id", "unknown"),
    )
    return result


@worker.attest(AttestationMode.SENSOR_WITNESS)
async def attest_pose_and_weight(claim_id: str, task: dict) -> dict:
    return {
        "kind": "indoor_pose_track",
        "payload": {
            "track": [
                {"t": "2026-06-01T10:00:00Z", "x": 0.0, "y": 0.0},
                {"t": "2026-06-01T10:02:00Z", "x": 15.0, "y": 5.0},
            ],
            "weight_delta_kg": 12.4,
        },
    }


@worker.attest(AttestationMode.THIRD_PARTY_WITNESS)
async def attest_beacon(claim_id: str, task: dict) -> dict:
    payload = task.get("descriptor_payload", {}) or {}
    return {
        "kind": "iot_beacon_proximity",
        "payload": {
            "beacon_id": f"beacon-{payload.get('destination')}",
            "rssi": -42,
            "observed_at": datetime.now(timezone.utc).isoformat(),
        },
    }


# --- The AMR's onboard RobotAgent ------------------------------------------

async def _post_place_on_shelf_continuation(
    *, prior_claim_id: str, destination: str, component_id: str
) -> None:
    """Post a follow-up place_on_shelf task from the AMR's onboard agent.

    This function is the load-bearing piece of the robot-as-agent pattern:
    a RobotAgent runs INSIDE the AMR worker's process, and after the
    transport attests, it publishes the next task in the chain.
    """
    robot = RobotAgent(
        name="amr-line-7-onboard-planner",
        coordinator="ws://localhost:8000/wcp/ws",
        agent_class="embodied_agent",
    )
    async with robot:
        descriptor = robot.build_continuation(
            prior_claim_id=prior_claim_id,
            descriptor_type="place_on_shelf",
            descriptor_payload={
                "component_id": component_id,
                "destination_workstation": destination,
                "shelf_orientation_deg": 0,
            },
            required_evidence_kinds=["indoor_pose_track", "weight_delta"],
            constraints={
                "time_window": {
                    "earliest": datetime.now(timezone.utc).isoformat(),
                    "latest": (
                        datetime.now(timezone.utc) + timedelta(minutes=15)
                    ).isoformat(),
                },
                "worker_class_filter": {"allowed": ["semi_autonomous"]},
            },
            attestation_requirement={
                "modes": ["sensor-witness", "owner-sign-off"],
                "threshold": "M-of-N",
                "M": 2,
                "N": 2,
                "evidence_schema": [
                    {
                        "mode": "sensor-witness",
                        "kinds": ["manipulator_pose_track", "weight_delta"],
                    },
                    {
                        "mode": "owner-sign-off",
                        "kinds": ["workstation_supervisor_signoff"],
                    },
                ],
                "override_authority": "did:wcp:line-supervisor",
                "override_audit_required": True,
            },
            settlement={
                "currency": "USD",
                "amount": "0.00",
                "escrow_provider": "internal-cost-allocation",
                "split": [
                    {
                        "party": "did:wcp:cost-center-line-7-manipulator-ops",
                        "pct": 100,
                    }
                ],
            },
        )
        result = await robot.post_continuation(
            prior_claim_id=prior_claim_id,
            descriptor=descriptor,
            bond_ref=f"onboard-bond-{uuid.uuid4()}",
            expiry=(
                datetime.now(timezone.utc) + timedelta(hours=1)
            ).isoformat(),
        )
        print(
            f"[amr-onboard-agent] posted place_on_shelf continuation; "
            f"task_id={result.get('task_id')} continuation_of={prior_claim_id}"
        )


if __name__ == "__main__":
    worker.run()
