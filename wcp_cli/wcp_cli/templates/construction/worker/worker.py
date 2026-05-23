"""WCP worker scaffold: {{NAME}} ({{CLASS}}, domain=construction).

Domain: construction inspection.
Typical use cases: site-progress drone surveys, daily safety walks, equipment-location audits.

Adjacent domains using the same protocol: infrastructure, manufacturing.
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
    descriptor_types=['observe_and_report', 'scheduled_presence'],
    certifications=[],
    class_extension={"domain": "construction"},
)
def declare() -> None:
    """Capability declaration; called at startup and on profile changes."""


@worker.handle("observe_and_report")
async def handle_primary(task: dict) -> dict:
    payload = task.get("descriptor_payload", {})
    # Replace with domain-appropriate execution.
    await asyncio.sleep(0.1)
    return {"completed_at": datetime.now(timezone.utc).isoformat(), "domain": "construction"}


@worker.attest(AttestationMode.SENSOR_WITNESS)
async def attest_primary(claim_id: str, task: dict) -> dict:
    return {
        "kind": "photo_with_exif",
        "payload": {"photo_hash": "demo", "exif": {"datetime": "2026-06-01T10:00:00Z"}},
    }


if __name__ == "__main__":
    worker.run()
