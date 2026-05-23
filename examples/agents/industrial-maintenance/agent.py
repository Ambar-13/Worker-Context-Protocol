"""industrial-maintenance agent: schedule cooling-tower-bearing thermal inspection."""
from __future__ import annotations
import asyncio, uuid
from datetime import datetime, timedelta, timezone
from wcp_sdk.v2 import Agent

agent = Agent(name="plant-ops-agent", coordinator="ws://localhost:8000/wcp/ws")


def build_thermal_inspection(asset_id: str) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "schema_version": "wcp/1.0-rc1",
        "task_id": str(uuid.uuid4()),
        "posted_by": agent.did,
        "descriptor_type": "observe_and_report",
        "descriptor_payload": {
            "asset_id": asset_id,
            "sensor_classes": ["thermal_ir", "rgb_camera"],
            "scope": {"venue_id": "cooling-tower-3", "zone_id": "deck-c"},
            "sampling": "thermal sweep then RGB closeup per bearing race",
            "deliverable_schema": "wcp/observation/1.0-rc1",
        },
        "constraints": {
            "time_window": {"earliest": now.isoformat(),
                            "latest": (now + timedelta(hours=12)).isoformat()},
            "worker_class_filter": {"allowed": ["human", "autonomous_robot", "hybrid"]},
        },
        "attestation_requirement": {
            "modes": ["sensor-witness", "third-party-witness"],
            "threshold": "M-of-N", "M": 2, "N": 2,
            "evidence_schema": [
                {"mode": "sensor-witness", "kinds": ["signed_sensor_recording"]},
                {"mode": "third-party-witness", "kinds": ["customer_signature"]},
            ],
            "override_authority": "did:wcp:example-plant-ops",
            "override_audit_required": True,
        },
        "settlement": {
            "currency": "USD", "amount": "450.00", "escrow_provider": "example-escrow",
            "split": [
                {"party": "did:wcp:inspector-pool", "pct": 70},
                {"party": "did:wcp:plant-operator", "pct": 25},
                {"party": "did:wcp:industrial-insurance-pool", "pct": 5},
            ],
        },
        "supervision": {"default": "autonomous"},
        "x-subcontract-allowed": False,
    }


async def main() -> None:
    async with agent:
        task = build_thermal_inspection("bearing-tower-3-deck-c")
        res = await agent.post_task(
            task,
            bond_ref=f"example-bond-{task['task_id']}",
            expiry=(datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
        )
        print(f"[agent] posted thermal inspection task_id={res['task_id']} "
              f"({res['eligible_workers_count']} eligible workers)")


if __name__ == "__main__":
    asyncio.run(main())
