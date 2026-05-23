"""healthcare-logistics agent: dispatch a medical-specimen transport."""
from __future__ import annotations
import asyncio, uuid
from datetime import datetime, timedelta, timezone
from wcp_sdk.v2 import Agent

agent = Agent(name="specimen-dispatch-agent", coordinator="ws://localhost:8000/wcp/ws")


def build_specimen_transport(specimen_id: str, pickup: str, dropoff: str) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "schema_version": "wcp/0.2",
        "task_id": str(uuid.uuid4()),
        "posted_by": agent.did,
        "descriptor_type": "transport",
        "descriptor_payload": {
            "specimen_id": specimen_id, "pickup": pickup, "dropoff": dropoff,
            "payload_description": "ambient-stable blood-tube panel",
            "handoff_protocol": "chain_of_custody_signed_at_both_endpoints",
            "cold_chain_requirement": {"min_c": 2, "max_c": 8, "max_excursion_minutes": 5},
        },
        "constraints": {
            "time_window": {"earliest": now.isoformat(),
                            "latest": (now + timedelta(hours=3)).isoformat()},
            "worker_class_filter": {"allowed": ["human", "hybrid", "autonomous_robot"]},
        },
        "attestation_requirement": {
            "modes": ["sensor-witness", "owner-sign-off"],
            "threshold": "M-of-N", "M": 2, "N": 2,
            "evidence_schema": [
                {"mode": "sensor-witness", "kinds": ["signed_sensor_recording"]},
                {"mode": "owner-sign-off", "kinds": ["whatsapp_business_signed_link"]},
            ],
        },
                "supervision": {"default": "autonomous"},
        "max_attestation_attempts": 1,
        "marketplace_ref": "external-allocation",
        "x-subcontract-allowed": False,
    }


async def main() -> None:
    async with agent:
        task = build_specimen_transport("SPM-2026-05-23-019",
                                        "draw-site-N3", "reference-lab-central")
        res = await agent.post_task(
            task,
            expiry=(datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
        )
        print(f"[agent] posted specimen-transport task_id={res['task_id']} "
              f"({res['eligible_workers_count']} eligible workers)")


if __name__ == "__main__":
    asyncio.run(main())
