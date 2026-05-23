"""WCP worker scaffold: {{NAME}} ({{CLASS}}, domain={{DOMAIN}}).

Generic baseline. Implements one descriptor handler and one attestation
provider. Replace the body of `handle_task` and `prove_completion` for
your application-layer semantics.
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
    descriptor_types=["scheduled_presence", "observe_and_report"],
    certifications=[],
    class_extension={"notes": "scaffolded by `wcp init worker`"},
)
def declare() -> None:
    """Capability declaration; called at startup and on profile changes."""


@worker.handle("scheduled_presence")
async def handle_scheduled_presence(task: dict) -> dict:
    payload = task.get("descriptor_payload", {})
    duration_min = int(payload.get("duration_minutes", 5))
    # Production workers do real work here. This scaffold simulates.
    await asyncio.sleep(min(duration_min, 2))
    return {"completed_at": datetime.now(timezone.utc).isoformat()}


@worker.handle("observe_and_report")
async def handle_observe(task: dict) -> dict:
    payload = task.get("descriptor_payload", {})
    return {
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "scope": payload.get("scope", {}),
    }


@worker.attest(AttestationMode.CRYPTOGRAPHIC_PRESENCE)
async def attest_presence(claim_id: str, task: dict) -> dict:
    now = datetime.now(timezone.utc)
    duration_min = int(task.get("descriptor_payload", {}).get("duration_minutes", 5))
    earlier = now.replace(microsecond=0)
    return {
        "kind": "geofence_check_in_out",
        "payload": {
            "check_in_at": earlier.isoformat(),
            "check_out_at": now.isoformat(),
            "region": {"polygon": [[0, 0], [10, 0], [10, 10], [0, 10]]},
        },
    }


if __name__ == "__main__":
    worker.run()
