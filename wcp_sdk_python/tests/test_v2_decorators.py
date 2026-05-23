"""v2 decorator-style API surface tests (no live coordinator)."""
from __future__ import annotations

from wcp_sdk.types import AttestationMode, WorkerClass
from wcp_sdk.v2 import Agent, Coordinator, Worker


def test_worker_construction_uses_default_identity():
    w = Worker(name="test", worker_class="human", coordinator="ws://localhost/wcp/ws")
    assert w.did.startswith("did:wcp:")
    assert w.worker_class == WorkerClass.HUMAN


def test_worker_capability_decorator_records_descriptor_types():
    w = Worker(name="t", worker_class="autonomous_robot", coordinator="ws://x")

    @w.capability(descriptor_types=["transport", "scheduled_presence"])
    def declare() -> None:
        return None

    descriptor = w.build_descriptor()
    out = descriptor.to_dict()
    assert out["class"] == "autonomous_robot"
    assert "wcp_sdk_v2_descriptor_types" in out["class_extension"]
    assert set(out["class_extension"]["wcp_sdk_v2_descriptor_types"]) == {
        "transport",
        "scheduled_presence",
    }


def test_worker_handle_decorator_registers_handler():
    w = Worker(name="t", worker_class="human", coordinator="ws://x")
    calls: list[dict] = []

    @w.handle("scheduled_presence")
    async def h(task: dict) -> dict:
        calls.append(task)
        return {"ok": True}

    assert "scheduled_presence" in w._handlers


def test_worker_attest_decorator_registers_provider():
    w = Worker(name="t", worker_class="human", coordinator="ws://x")

    @w.attest(AttestationMode.CRYPTOGRAPHIC_PRESENCE)
    async def a(claim_id: str, task: dict) -> dict:
        return {"kind": "geofence_check_in_out", "payload": {}}

    assert AttestationMode.CRYPTOGRAPHIC_PRESENCE in w._attesters


def test_worker_attest_accepts_string_mode():
    w = Worker(name="t", worker_class="human", coordinator="ws://x")

    @w.attest("sensor-witness")
    async def a(claim_id: str, task: dict) -> dict:
        return {"kind": "gps_track", "payload": {"track": []}}

    assert AttestationMode.SENSOR_WITNESS in w._attesters


def test_agent_task_builder_decorator():
    a = Agent(name="t", coordinator="ws://x")

    @a.task_builder()
    def build() -> dict:
        return {"task_id": "demo"}

    assert a._task_builder is build


def test_agent_on_capability_decorator():
    a = Agent(name="t", coordinator="ws://x")
    seen: list[dict] = []

    @a.on_capability(filter={"class": "human"})
    async def h(event: dict) -> None:
        seen.append(event)

    assert len(a._capability_handlers) == 1
    f, _fn = a._capability_handlers[0]
    assert f == {"class": "human"}


def test_coordinator_registry_records_extensions():
    c = Coordinator()
    c.register_attestation_verifier("custom-mode", lambda *args: {})
    c.register_settlement_adapter("custom-escrow", object())
    c.add_federation_trust_anchor({"peer_coordinator_did": "did:wcp:peer"})
    assert "custom-mode" in c.attestation_verifiers
    assert "custom-escrow" in c.settlement_adapters
    assert len(c.federation_trust_anchors) == 1
