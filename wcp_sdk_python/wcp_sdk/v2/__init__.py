"""
WCP Python SDK v2: decorator-style three-role API.

ADDITIVE to v1 (`wcp_sdk.WorkerSession`, `wcp_sdk.AgentSession`). v1 imports
continue to work; deprecation warnings on direct v1 use are emitted on import.

Three roles:

    from wcp_sdk.v2 import Worker, Agent, Coordinator

Worker example:

    worker = Worker(name="my-worker", worker_class="human", coordinator="ws://...")

    @worker.capability(descriptor_types=["scheduled_presence"])
    def declare():
        ...

    @worker.handle("scheduled_presence")
    async def execute(task: dict) -> dict:
        await do_work()
        return {"completed_at": now()}

    @worker.attest(AttestationMode.CRYPTOGRAPHIC_PRESENCE)
    async def prove(claim_id, task) -> dict:
        return {"kind": "geofence_check_in_out", "payload": {...}}

    worker.run()

Agent example:

    agent = Agent(name="my-agent", coordinator="ws://...")
    async with agent:
        result = await agent.post_task(task, bond_ref=..., expiry=...)

Coordinator example (extension points):

    from wcp_sdk.v2 import Coordinator
    coord = Coordinator()
    coord.register_attestation_verifier("custom-mode", my_verifier_fn)
    coord.register_settlement_adapter("custom-escrow", MyAdapter())
"""

from .worker import Worker
from .agent import Agent
from .coordinator import Coordinator

__all__ = ["Worker", "Agent", "Coordinator"]
