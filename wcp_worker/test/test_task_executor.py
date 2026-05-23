"""Smoke tests for the task executor (ROS 2-independent; uses simulated nav)."""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest

from wcp_worker.attestation_collector import AttestationCollector
from wcp_worker.identity import WorkerIdentity
from wcp_worker.nav_adapter import NavAdapter
from wcp_worker.task_executor import TaskExecutor


class StubRpc:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.attest_response = {"verifier_decision": "pass"}

    async def call(self, method: str, params: dict[str, Any] | None = None):
        params = params or {}
        self.calls.append((method, params))
        if method == "tasks/attest":
            return self.attest_response
        return {"ok": True}


@pytest.mark.asyncio
async def test_executor_runs_transport(tmp_path: Path) -> None:
    ident = WorkerIdentity.load_or_generate(tmp_path / "key")
    rpc = StubRpc()
    nav = NavAdapter(None, simulated_duration_seconds=0.01)
    collector = AttestationCollector(ident)
    ex = TaskExecutor(ident, rpc, nav, collector)
    task = {
        "task_id": "t1",
        "descriptor_type": "transport",
        "descriptor_payload": {
            "pickup": {"pose": [0.0, 0.0, 0.0]},
            "dropoff": {"pose": [5.0, 5.0, 0.0]},
        },
    }
    res = await ex.execute(claim_id="c1", task=task)
    assert res["verifier_decision"] == "pass"
    methods = [m for m, _ in rpc.calls]
    assert "tasks/execute" in methods
    assert "tasks/attest" in methods


@pytest.mark.asyncio
async def test_executor_runs_scheduled_presence(tmp_path: Path) -> None:
    ident = WorkerIdentity.load_or_generate(tmp_path / "key")
    rpc = StubRpc()
    nav = NavAdapter(None, simulated_duration_seconds=0.01)
    collector = AttestationCollector(ident)
    ex = TaskExecutor(ident, rpc, nav, collector)
    task = {
        "task_id": "t2",
        "descriptor_type": "scheduled_presence",
        "descriptor_payload": {"duration_minutes": 1, "region": {"polygon": []}},
    }
    res = await ex.execute(claim_id="c2", task=task)
    assert res["verifier_decision"] == "pass"
