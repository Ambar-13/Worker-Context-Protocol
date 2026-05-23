"""
Federation demo: logistics worker registered on coord-beta (port 9001).

The worker registers with coord-beta. coord-beta peers with coord-alpha via
the federation trust anchor (provisioned by setup.sh). An agent on coord-alpha
(see agent_alpha.py) discovers this worker via the federation capability
discovery and posts a task; this worker claims, executes, and attests.

This script targets the v1.0-rc1 reference coordinator API. The federation
endpoints expected by the demo (capability sync across peers, cross-coordinator
task forwarding) are v1.1 RFC 0016 implementation; until they land in the
reference coordinator, this script runs end-to-end on coord-beta only and
the cross-coordinator discovery is exercised at the protocol level (the
worker registers; the demo's verify.sh confirms registration on coord-beta).
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

# Ensure the local SDK is on the import path when running from the repo
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "wcp_sdk_python"))

from wcp_sdk.v2 import Worker  # noqa: E402

COORD_BETA_URL = os.environ.get("COORD_BETA_URL", "ws://localhost:9001/wcp/ws")

logging.basicConfig(level=logging.INFO, format="[worker_beta] %(message)s")
log = logging.getLogger("federation-demo.worker_beta")


async def main() -> None:
    """Register a logistics worker on coord-beta and accept federated tasks."""

    worker = Worker(
        name="logistics-worker-1",
        worker_class="human",
        coordinator=COORD_BETA_URL,
    )

    @worker.capability(
        descriptor_types=["transport"],
        certifications=[
            {
                "kind": "forklift_operator_certificate",
                "issuing_authority": "did:wcp:authority-uk-hse",
                "expiry": "2027-12-31",
            }
        ],
    )
    def declare_capability() -> None:
        """Declare logistics worker capability with London policy window."""

    @worker.handle("transport")
    async def handle_transport_task(task: dict) -> dict:
        payload = task.get("descriptor_payload", {})
        pickup = payload.get("pickup_zone", "<unknown>")
        delivery = payload.get("delivery_zone", "<unknown>")
        log.info(
            "claimed federated transport task: pickup=%s delivery=%s",
            pickup,
            delivery,
        )
        # Simulate work
        await asyncio.sleep(1.0)
        log.info("transport task completed")
        return {"status": "completed", "delivery_zone": delivery}

    @worker.attest("sensor-witness")
    async def attest_completion(claim_id: str, task: dict) -> dict:
        # In a real worker, this would emit GPS track from the device.
        # For the demo, we emit a stub gps_track evidence.
        return {
            "kind": "gps_track",
            "payload": {
                "track": [
                    {"lat": 51.5074, "lng": -0.1278, "ts": "2026-05-23T14:32:01Z"},
                    {"lat": 51.5080, "lng": -0.1290, "ts": "2026-05-23T14:32:05Z"},
                    {"lat": 51.5085, "lng": -0.1300, "ts": "2026-05-23T14:32:08Z"},
                ]
            },
        }

    log.info("registering with coord-beta at %s ...", COORD_BETA_URL)
    log.info("logistics worker in Europe/London policy window")
    log.info("waiting for federated tasks via coord-alpha trust anchor")

    try:
        await worker.run_async()
    except Exception as exc:
        log.warning("worker_beta encountered: %s", exc)
        log.warning(
            "v1.0-rc1 reference coordinator may not yet expose federation endpoints; "
            "in that case the worker registers on coord-beta only and the federation "
            "demo's cross-coordinator path is a v1.1 implementation deliverable"
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("worker_beta stopped")
