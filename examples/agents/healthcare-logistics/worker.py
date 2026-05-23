"""healthcare-logistics worker: a courier with a regulated cold-chain container."""
from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from wcp_sdk.types import AttestationMode
from wcp_sdk.v2 import Worker

worker = Worker(name="specimen-courier-3", worker_class="hybrid",
                coordinator="ws://localhost:8000/wcp/ws")


@worker.capability(
    descriptor_types=["transport"],
    certifications=[
        {"issuer": "example-health-authority", "id": "COLD-CHAIN-COURIER-2026", "expires": "2027-12-31"},
    ],
    class_extension={
        "role": "specimen_courier", "equipment": ["cold_chain_box_2_8C", "GPS_tracker"],
        "payload": {"max_kg": 5, "regulated_classes": ["specimen", "blood_products"]},
    },
)
def declare() -> None: ...


@worker.handle("transport")
async def transport_specimen(task: dict) -> dict:
    p = task.get("descriptor_payload", {})
    print(f"[worker] transporting specimen from {p.get('pickup')} to {p.get('dropoff')}")
    await asyncio.sleep(0.4)
    return {"delivered_at": datetime.now(timezone.utc).isoformat()}


@worker.attest(AttestationMode.SENSOR_WITNESS)
async def attest_temp_log(claim_id: str, task: dict) -> dict:
    return {"kind": "signed_sensor_recording",
            "payload": {"recording_hash": "demo-temp-log-hash",
                        "duration_seconds": 1800}}


@worker.attest(AttestationMode.OWNER_SIGN_OFF)
async def attest_chain_of_custody(claim_id: str, task: dict) -> dict:
    return {"kind": "whatsapp_business_signed_link",
            "payload": {"signing_party_did": "did:wcp:example-receiving-lab-tech",
                        "signed_token": "demo-chain-of-custody-token",
                        "issued_at": datetime.now(timezone.utc).isoformat()}}


if __name__ == "__main__":
    worker.run()
