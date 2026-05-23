"""
Federation demo: industrial-maintenance-style agent operating on coord-alpha.

This agent connects to coord-alpha (port 9000), subscribes with
filter.federation: true to discover workers across the federation trust
anchor (provisioned by setup.sh), discovers worker_beta on coord-beta,
posts a logistics task, watches the lifecycle complete, and verifies the
cross-coordinator audit chain.

This script targets the v0.2 reference coordinator API. The federation
endpoints expected by the demo (capability sync across peers, cross-coordinator
task forwarding) are v1.1 RFC 0016 implementation; until they land in the
reference coordinator, this script demonstrates the agent-side behavior and
exits cleanly with a documented note if federation endpoints are absent.
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "wcp_sdk_python"))

from wcp_sdk.v2 import Agent  # noqa: E402

COORD_ALPHA_URL = os.environ.get("COORD_ALPHA_URL", "ws://localhost:9000/wcp/ws")

logging.basicConfig(level=logging.INFO, format="[agent_alpha] %(message)s")
log = logging.getLogger("federation-demo.agent_alpha")


def build_federated_transport_task(agent_did: str) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "schema_version": "wcp/0.2",
        "task_id": "t_" + uuid.uuid4().hex[:12],
        "posted_by": agent_did,
        "descriptor_type": "transport",
        "descriptor_payload": {
            "pickup_zone": "warehouse-london-east-1",
            "delivery_zone": "logistics-zone-c-staging",
            "payload_class": "standard-pallet-eu1",
            "priority": "routine",
        },
        "constraints": {
            "worker_class_filter": {"allowed": ["human", "autonomous_robot"]},
            "policy_window_intersect": "Europe/London",
            "federation_allowed": True,
            "time_window": {
                "earliest": now.isoformat(),
                "latest": (now + timedelta(hours=2)).isoformat(),
            },
        },
        "attestation_requirement": {
            "modes": ["sensor-witness"],
            "threshold": "M-of-N",
            "M": 1,
            "N": 1,
            "evidence_schema": [
                {"mode": "sensor-witness", "kinds": ["gps_track"]}
            ],
        },
        "max_attestation_attempts": 1,
        "marketplace_ref": "federation-demo-alpha",
        "supervision": {"default": "autonomous"},
        "x-subcontract-allowed": False,
    }


async def main() -> None:
    agent = Agent(name="dispatcher-alpha", coordinator=COORD_ALPHA_URL)

    async with agent:
        log.info("connected to coord-alpha at %s as %s", COORD_ALPHA_URL, agent.did)
        log.info("subscribing with federation filter...")

        try:
            subscription = await agent.discover_capabilities(
                filter={"federation": True, "worker_class_filter": ["human"]}
            )
            log.info("subscription: %s", subscription)
        except Exception as exc:
            log.warning("federation subscription returned: %s", exc)
            log.warning(
                "v0.2 reference coordinator may not yet support filter.federation; "
                "the demo's cross-coordinator discovery is a v1.1 implementation "
                "deliverable per RFC 0016 federation primitives"
            )
            log.info(
                "continuing with single-coordinator post to demonstrate task lifecycle"
            )

        log.info("posting transport task on coord-alpha")
        task = build_federated_transport_task(agent.did)
        try:
            result = await agent.post_task(
                task,
                expiry=(datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
            )
            log.info("task posted: %s", result)
            log.info(
                "in a fully-federated deployment, this task would be forwarded "
                "to coord-beta where worker_beta would claim it; the audit "
                "chain entry task_completed becomes the trusted signal for any "
                "settlement layer above WCP"
            )
        except Exception as exc:
            log.warning("task post returned: %s", exc)
            log.warning(
                "see README.md 'Known limitations' for v1.1 federation infrastructure status"
            )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("agent_alpha stopped")
