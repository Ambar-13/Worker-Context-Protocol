"""field-research agent: dispatch a sample-collection route."""
from __future__ import annotations
import asyncio, uuid
from datetime import datetime, timedelta, timezone
from wcp_sdk.v2 import Agent

agent = Agent(name="watershed-monitoring-agent", coordinator="ws://localhost:8000/wcp/ws")


def build_sample_route(sites: list[dict]) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "schema_version": "wcp/1.0-rc1",
        "task_id": str(uuid.uuid4()),
        "posted_by": agent.did,
        "descriptor_type": "observe_and_report",
        "descriptor_payload": {
            "sites": sites,
            "sample_protocol": "ISO-5667-style grab samples with in-situ multiparameter probe",
            "sensor_classes": ["multiparameter_sonde", "rgb_camera"],
            "deliverable_schema": "wcp/observation/1.0-rc1",
        },
        "constraints": {
            "time_window": {"earliest": now.isoformat(),
                            "latest": (now + timedelta(hours=10)).isoformat()},
            "worker_class_filter": {"allowed": ["human", "autonomous_robot"]},
        },
        "attestation_requirement": {
            "modes": ["sensor-witness"],
            "threshold": "M-of-N", "M": 2, "N": 2,
            "evidence_schema": [
                {"mode": "sensor-witness", "kinds": ["gps_track", "signed_sensor_recording"]},
            ],
            "override_authority": "did:wcp:example-watershed-pi",
            "override_audit_required": True,
        },
        "settlement": {
            "currency": "USD", "amount": "280.00", "escrow_provider": "example-grant-escrow",
            "split": [{"party": "did:wcp:researcher-pool", "pct": 95},
                      {"party": "did:wcp:research-org-platform", "pct": 5}],
        },
        "supervision": {"default": "autonomous"},
        "x-subcontract-allowed": False,
    }


async def main() -> None:
    async with agent:
        task = build_sample_route([
            {"site_id": "WS-N-001", "lat": 1.330, "lon": 103.770},
            {"site_id": "WS-N-002", "lat": 1.340, "lon": 103.780},
            {"site_id": "WS-N-003", "lat": 1.350, "lon": 103.790},
        ])
        res = await agent.post_task(
            task,
            bond_ref=f"example-bond-{task['task_id']}",
            expiry=(datetime.now(timezone.utc) + timedelta(hours=12)).isoformat(),
        )
        print(f"[agent] posted sample-route task_id={res['task_id']} "
              f"({res['eligible_workers_count']} eligible workers)")


if __name__ == "__main__":
    asyncio.run(main())
