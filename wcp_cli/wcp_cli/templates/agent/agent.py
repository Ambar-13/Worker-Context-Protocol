"""WCP agent scaffold: {{NAME}} (llm={{LLM}}).

A minimal AI-agent application that posts a task and waits for attestation.
Replace the LLM call and the descriptor body with your application.
"""
from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timedelta, timezone

from wcp_sdk.v2 import Agent
from wcp_sdk.types import AttestationMode, WorkerClass

COORDINATOR = "{{COORDINATOR}}"

agent = Agent(name="{{NAME}}", coordinator=COORDINATOR)


@agent.task_builder()
def build_demo_task() -> dict:
    """Build a TaskDescriptor for a demo dispatch. Customize for your domain."""
    now = datetime.now(timezone.utc)
    return {
        "schema_version": "wcp/1.0-rc1",
        "task_id": str(uuid.uuid4()),
        "posted_by": agent.did,
        "descriptor_type": "scheduled_presence",
        "descriptor_payload": {"duration_minutes": 5, "location": "zone-a"},
        "constraints": {
            "time_window": {
                "earliest": now.isoformat(),
                "latest": (now + timedelta(hours=2)).isoformat(),
            },
            "worker_class_filter": {
                "allowed": [c.value for c in WorkerClass]
            },
        },
        "attestation_requirement": {
            "modes": [AttestationMode.CRYPTOGRAPHIC_PRESENCE.value],
            "threshold": "M-of-N",
            "M": 1,
            "N": 1,
            "evidence_schema": [
                {
                    "mode": "cryptographic-presence",
                    "kinds": ["geofence_check_in_out"],
                }
            ],
            "override_authority": "did:wcp:example-operator-ops",
            "override_audit_required": True,
        },
        "settlement": {
            "currency": "USD",
            "amount": "100.00",
            "escrow_provider": "example-escrow",
            "split": [
                {"party": "did:wcp:worker-principal", "pct": 80},
                {"party": "did:wcp:platform", "pct": 15},
                {"party": "did:wcp:insurance-pool", "pct": 5},
            ],
        },
        "supervision": {"default": "autonomous"},
        "x-subcontract-allowed": False,
    }


async def main() -> None:
    async with agent:
        task = build_demo_task()
        result = await agent.post_task(
            task,
            bond_ref=f"example-bond-{task['task_id']}",
            expiry=(datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
        )
        print(f"posted task {result['task_id']}; "
              f"{result['eligible_workers_count']} eligible workers")


if __name__ == "__main__":
    asyncio.run(main())
