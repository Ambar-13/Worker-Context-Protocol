"""WCP worker scaffold: {{NAME}} ({{CLASS}}, domain=logistics).

Domain: warehouse and supply-chain operations.
Typical use cases: pallet moves, dock-to-stock transfers, cross-dock relays.

Adjacent domains using the same protocol: manufacturing, industrial.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from wcp_sdk.v2 import Worker
from wcp_sdk.types import AttestationMode

worker = Worker(
    name="{{NAME}}",
    worker_class="{{CLASS}}",
    coordinator="{{COORDINATOR}}",
)


@worker.capability(
    descriptor_types=['transport'],
    certifications=[],
    class_extension={"domain": "logistics"},
)
def declare() -> None:
    """Capability declaration; called at startup and on profile changes."""


@worker.handle("transport")
async def handle_primary(task: dict) -> dict:
    payload = task.get("descriptor_payload", {})
    # Replace with domain-appropriate execution.
    await asyncio.sleep(0.1)
    return {"completed_at": datetime.now(timezone.utc).isoformat(), "domain": "logistics"}


@worker.attest(AttestationMode.SENSOR_WITNESS)
async def attest_primary(claim_id: str, task: dict) -> dict:
    return {
        "kind": "indoor_pose_track",
        "payload": {"track": [{"t": "2026-06-01T10:00:00Z", "x": 0.0, "y": 0.0}]},
    }


if __name__ == "__main__":
    worker.run()
