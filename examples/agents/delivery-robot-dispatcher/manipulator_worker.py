"""Stationary manipulator at the workstation. Claims the place_on_shelf
follow-up task posted by the AMR's onboard RobotAgent.

The manipulator is a different worker class (semi_autonomous) from the
AMR (autonomous_robot). The same coordinator routes the AMR's posted
continuation to the manipulator because the AMR did not restrict the
worker class; the manipulator's runbook checks `continuation_of` and
optionally reads the prior task's audit chain entries before claiming.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from wcp_sdk.types import AttestationMode
from wcp_sdk.v2 import Worker

worker = Worker(
    name="manipulator-ws7",
    worker_class="semi_autonomous",
    coordinator="ws://localhost:8000/wcp/ws",
)


@worker.capability(
    descriptor_types=["place_on_shelf"],
    certifications=[
        {"issuer": "facility-manipulator-cert", "id": "MANIP-LINE-7-2026"}
    ],
    class_extension={
        "kinematics": {
            "type": "stationary_arm",
            "degrees_of_freedom": 7,
            "reach_m": 1.6,
        },
        "payload": {"max_kg": 50},
        "end_effectors": [
            {
                "class": "gripper",
                "rated_for": ["component_tray", "small_box"],
            }
        ],
        # Continuation-aware: this worker can read continuation_of and act
        # on the prior task's evidence kinds.
        "continuation_aware": True,
    },
)
def declare() -> None:
    return None


@worker.handle("place_on_shelf")
async def place(task: dict) -> dict:
    payload = task.get("descriptor_payload", {}) or {}
    cont = task.get("continuation_of", {}) or {}
    print(
        f"[manipulator] placing component "
        f"{payload.get('component_id')} on shelf at "
        f"{payload.get('destination_workstation')}; "
        f"continuation_of={cont.get('claim_id')}"
    )
    await asyncio.sleep(0.3)
    return {"placed_at": datetime.now(timezone.utc).isoformat()}


@worker.attest(AttestationMode.SENSOR_WITNESS)
async def attest_manipulator(claim_id: str, task: dict) -> dict:
    return {
        "kind": "manipulator_pose_track",
        "payload": {
            "joint_states": [
                {"t": "2026-06-01T10:03:00Z", "q": [0.0] * 7},
                {"t": "2026-06-01T10:03:15Z", "q": [0.1, 0.5, -0.2, 0.8,
                                                    0.0, 0.3, 0.0]},
            ],
            "weight_delta_kg": -12.4,
        },
    }


@worker.attest(AttestationMode.OWNER_SIGN_OFF)
async def attest_signoff(claim_id: str, task: dict) -> dict:
    return {
        "kind": "workstation_supervisor_signoff",
        "payload": {
            "signed_by": "did:wcp:line-7-supervisor",
            "signed_at": datetime.now(timezone.utc).isoformat(),
            "confirmed": True,
        },
    }


if __name__ == "__main__":
    worker.run()
