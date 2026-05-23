"""WCP worker scaffold: {{NAME}} ({{CLASS}}, domain=maritime).

Domain: maritime and subsea operations.
Typical use cases: ROV inspection runs, buoy maintenance, hull surveys, supply transfers.

Adjacent domains using the same protocol: research, infrastructure.
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
    descriptor_types=['observe_and_report', 'transport'],
    certifications=[],
    class_extension={"domain": "maritime"},
)
def declare() -> None:
    """Capability declaration; called at startup and on profile changes."""


@worker.handle("observe_and_report")
async def handle_primary(task: dict) -> dict:
    payload = task.get("descriptor_payload", {})
    # Replace with domain-appropriate execution.
    await asyncio.sleep(0.1)
    return {"completed_at": datetime.now(timezone.utc).isoformat(), "domain": "maritime"}


@worker.attest(AttestationMode.SENSOR_WITNESS)
async def attest_primary(claim_id: str, task: dict) -> dict:
    return {
        "kind": "signed_sensor_recording",
        "payload": {"recording_hash": "demo", "duration_seconds": 60},
    }


if __name__ == "__main__":
    worker.run()
