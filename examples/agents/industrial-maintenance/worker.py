"""industrial-maintenance worker (hybrid: human inspector or wall-climbing AMR)."""
from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from wcp_sdk.types import AttestationMode
from wcp_sdk.v2 import Worker

worker = Worker(name="thermal-inspector-1", worker_class="hybrid",
                coordinator="ws://localhost:8000/wcp/ws")


@worker.capability(
    descriptor_types=["observe_and_report"],
    certifications=[{"issuer": "example-industry-cert", "id": "THERMAL-IR-L2", "expires": "2027-12-31"}],
    class_extension={"role": "bearing_inspector", "sensors": ["thermal_ir", "rgb"]},
)
def declare() -> None: ...


@worker.handle("observe_and_report")
async def inspect(task: dict) -> dict:
    target = task.get("descriptor_payload", {}).get("asset_id", "unknown")
    print(f"[worker] thermal-inspecting bearing {target}")
    await asyncio.sleep(0.3)
    return {"inspected_at": datetime.now(timezone.utc).isoformat(), "asset_id": target}


@worker.attest(AttestationMode.SENSOR_WITNESS)
async def attest_thermal(claim_id: str, task: dict) -> dict:
    return {"kind": "signed_sensor_recording",
            "payload": {"recording_hash": "demo-thermal-ir-hash", "duration_seconds": 120}}


@worker.attest(AttestationMode.THIRD_PARTY_WITNESS)
async def attest_supervisor(claim_id: str, task: dict) -> dict:
    return {"kind": "customer_signature",
            "payload": {"signed_text": "thermal inspection complete; no out-of-spec bearings",
                        "signature_image_hash": "demo-supervisor-sig-hash"}}


if __name__ == "__main__":
    worker.run()
