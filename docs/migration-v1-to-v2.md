# Migration: Python SDK v1 to v2

The v2 decorator-style API is **additive**. v1 code continues to work; v2 imports live under `wcp_sdk.v2`. The wire protocol is unchanged.

## What's new in v2

- `wcp_sdk.v2.Worker`, `wcp_sdk.v2.Agent`, `wcp_sdk.v2.Coordinator`: three-role classes.
- Decorators: `@worker.capability`, `@worker.handle`, `@worker.attest`, `@agent.task_builder`, `@agent.on_capability`.
- Coordinator extension points: `register_attestation_verifier`, `register_settlement_adapter`, `add_federation_trust_anchor`.

## Side-by-side: worker

v1:

```python
from wcp_sdk import WorkerSession, WorkerIdentity, AttestationMode

identity = WorkerIdentity.generate()
async with await WorkerSession.connect("ws://localhost:8000/wcp/ws", identity) as session:
    await session.publish_capabilities(descriptor)
    # manual claim/execute/attest loop
```

v2:

```python
from wcp_sdk.v2 import Worker
from wcp_sdk.types import AttestationMode

worker = Worker(
    name="my-worker",
    worker_class="autonomous_robot",
    coordinator="ws://localhost:8000/wcp/ws",
)

@worker.capability(descriptor_types=["transport"])
def declare(): ...

@worker.handle("transport")
async def execute(task): return {"delivered_at": "..."}

@worker.attest(AttestationMode.SENSOR_WITNESS)
async def prove(claim_id, task):
    return {"kind": "indoor_pose_track", "payload": {"track": []}}

worker.run()
```

## Side-by-side: agent

v1:

```python
from wcp_sdk import AgentSession, AgentIdentity
from wcp_sdk.session import make_task_descriptor

identity = AgentIdentity.generate()
async with await AgentSession.connect("ws://...", identity) as session:
    result = await session.post(task_descriptor, bond_ref=..., expiry=...)
```

v2:

```python
from wcp_sdk.v2 import Agent

agent = Agent(name="my-agent", coordinator="ws://localhost:8000/wcp/ws")
async with agent:
    result = await agent.post_task(task_dict, bond_ref=..., expiry=...)
```

## What stays the same

- Wire protocol (the 9 RPCs, `acceptance_attestation` signature, audit chain).
- Typed objects in `wcp_sdk.types` (CapabilityDescriptor, TaskDescriptor, AttestationEvidence).
- `wcp_sdk.canonical` (canonical JSON, SHA-256).
- `wcp_sdk.identity` (WorkerIdentity, AgentIdentity).
- `wcp_sdk.session.make_task_descriptor` ergonomic helper.

## When to migrate

- New projects: start on v2.
- Existing v1 code: no immediate need to migrate. v1 will continue to work for v1.x releases; deprecation horizon will be announced one minor release ahead of removal per `spec/semver-policy.md`.

## Compatibility

You can mix v1 and v2 in one process. The v2 `Worker.identity` is a v1 `WorkerIdentity`; the v2 `Agent` wraps a v1 `AgentSession` internally.
