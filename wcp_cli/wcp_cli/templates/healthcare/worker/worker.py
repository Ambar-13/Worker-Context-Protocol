"""WCP worker scaffold: {{NAME}} ({{CLASS}}, domain=healthcare).

Domain: regulated healthcare operations.
Typical use cases: specimen transport with cold-chain attestation, supply rounds, equipment relocation.

Adjacent domains using the same protocol: scientific, emergency.
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
    descriptor_types=['transport', 'scheduled_presence'],
    certifications=[],
    class_extension={"domain": "healthcare"},
)
def declare() -> None:
    """Capability declaration; called at startup and on profile changes."""


@worker.handle("transport")
async def handle_primary(task: dict) -> dict:
    payload = task.get("descriptor_payload", {})
    # Replace with domain-appropriate execution.
    await asyncio.sleep(0.1)
    return {"completed_at": datetime.now(timezone.utc).isoformat(), "domain": "healthcare"}


@worker.attest(AttestationMode.SENSOR_WITNESS)
async def attest_primary(claim_id: str, task: dict) -> dict:
    return {
        "kind": "gps_track",
        "payload": {"track": [{"t": "2026-06-01T10:00:00Z", "x": 0.0, "y": 0.0}]},
    }


if __name__ == "__main__":
    worker.run()
