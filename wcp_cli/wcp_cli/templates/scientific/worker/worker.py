"""WCP worker scaffold: {{NAME}} ({{CLASS}}, domain=scientific).

Domain: scientific lab operations.
Typical use cases: instrument calibration scheduling, sample preparation queues, autonomous experiment runners.

Adjacent domains using the same protocol: research, healthcare.
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
    descriptor_types=['scheduled_presence', 'observe_and_report'],
    certifications=[],
    class_extension={"domain": "scientific"},
)
def declare() -> None:
    """Capability declaration; called at startup and on profile changes."""


@worker.handle("scheduled_presence")
async def handle_primary(task: dict) -> dict:
    payload = task.get("descriptor_payload", {})
    # Replace with domain-appropriate execution.
    await asyncio.sleep(0.1)
    return {"completed_at": datetime.now(timezone.utc).isoformat(), "domain": "scientific"}


@worker.attest(AttestationMode.CRYPTOGRAPHIC_PRESENCE)
async def attest_primary(claim_id: str, task: dict) -> dict:
    return {
        "kind": "geofence_check_in_out",
        "payload": {"check_in_at": "2026-06-01T10:00:00Z", "check_out_at": "2026-06-01T10:05:00Z", "region": {"polygon": [[0,0],[10,0],[10,10],[0,10]]}},
    }


if __name__ == "__main__":
    worker.run()
