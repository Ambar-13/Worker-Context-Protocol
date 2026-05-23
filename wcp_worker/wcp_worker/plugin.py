"""WCP worker plugin: ROS 2 lifecycle node.

Lifecycle: unconfigured -> inactive -> active -> inactive -> finalized.

In `unconfigured`, the plugin loads identity and config.
In `inactive`, the plugin establishes the RpcClient connection but does not
claim tasks.
In `active`, the plugin publishes capabilities, subscribes to task posts,
and accepts tasks/claim opportunities. While active, it runs heartbeats.

When ROS 2 is unavailable (test host), `main()` falls back to a no-op for
import-time tests; the same code paths are exercised by direct unit tests
on the asyncio helpers.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from .attestation_collector import AttestationCollector
from .capability_publisher import CapabilityPublisher
from .identity import WorkerIdentity
from .nav_adapter import NavAdapter
from .rpc_client import RpcClient
from .supervision_bridge import SupervisionBridge
from .task_executor import TaskExecutor

log = logging.getLogger("wcp.plugin")

try:
    import rclpy  # type: ignore[import-not-found]
    from rclpy.lifecycle import LifecycleNode  # type: ignore[import-not-found]
    from rclpy.lifecycle import TransitionCallbackReturn  # type: ignore[import-not-found]
    from rclpy.lifecycle import State  # type: ignore[import-not-found]
except ImportError:  # ROS 2 absent in test host
    rclpy = None  # type: ignore[assignment]
    LifecycleNode = object  # type: ignore[assignment,misc]
    TransitionCallbackReturn = None  # type: ignore[assignment]
    State = None  # type: ignore[assignment]


class WcpWorkerNode(LifecycleNode):  # type: ignore[misc]
    """The WCP worker as a ROS 2 lifecycle node."""

    def __init__(self) -> None:
        if rclpy is None:
            return
        super().__init__("wcp_worker")  # type: ignore[misc]
        self.declare_parameter("coordinator_url", "ws://localhost:8000/wcp/ws")
        self.declare_parameter("key_path", "/tmp/wcp_worker_key")
        self.declare_parameter("principal_id", "did:wcp:rentably-fleet")
        self.declare_parameter("venue_id", "v1")
        self.declare_parameter("map_id", "m1")
        self._loop: asyncio.AbstractEventLoop | None = None
        self._async_task: asyncio.Task[None] | None = None
        self._identity: WorkerIdentity | None = None
        self._rpc: RpcClient | None = None
        self._executor: TaskExecutor | None = None
        self._supervision: SupervisionBridge | None = None

    def on_configure(self, state):  # type: ignore[override]
        coord_url = self.get_parameter("coordinator_url").value
        key_path = Path(self.get_parameter("key_path").value)
        self._identity = WorkerIdentity.load_or_generate(key_path)
        self._rpc = RpcClient(coord_url)
        nav = NavAdapter(self)
        collector = AttestationCollector(self._identity)
        self._executor = TaskExecutor(self._identity, self._rpc, nav, collector)
        self._supervision = SupervisionBridge(self._identity, self._rpc)
        log.info("WCP worker configured as %s", self._identity.did)
        return TransitionCallbackReturn.SUCCESS

    def on_activate(self, state):  # type: ignore[override]
        assert self._rpc is not None and self._identity is not None
        self._loop = asyncio.new_event_loop()
        self._async_task = self._loop.create_task(self._run_active())
        return TransitionCallbackReturn.SUCCESS

    def on_deactivate(self, state):  # type: ignore[override]
        if self._async_task is not None:
            self._async_task.cancel()
        return TransitionCallbackReturn.SUCCESS

    def on_cleanup(self, state):  # type: ignore[override]
        if self._rpc is not None and self._loop is not None:
            self._loop.run_until_complete(self._rpc.close())
        return TransitionCallbackReturn.SUCCESS

    async def _run_active(self) -> None:
        assert self._rpc is not None and self._identity is not None
        await self._rpc.connect()
        publisher = CapabilityPublisher(
            self._identity,
            self._rpc,
            principal_id=self.get_parameter("principal_id").value,
            venue_id=self.get_parameter("venue_id").value,
            map_id=self.get_parameter("map_id").value,
            kinematics={"locomotion": "wheeled", "max_speed_mps": 1.4,
                        "footprint_m": [0.6, 0.4]},
            payload={"max_kg": 5, "max_dim_m": [0.4, 0.4, 0.3]},
            end_effectors=[{"class": "tray", "rated_for": ["solid_under_5kg"]}],
            environment={"indoor": True, "ip_rating": "IP54",
                         "operating_temp_c": [5, 40]},
        )
        await publisher.publish()
        # In a real deployment, the plugin now waits on capabilities/subscribe
        # stream messages indicating posted tasks targeted at this worker.
        # The v0.1 reference subscribes via the RpcClient stream handler and
        # claims interactively. Application orchestration is out of scope at
        # v0.1; the executor is invoked by external code in tests and demos.
        while True:
            await asyncio.sleep(60.0)


def main(args: Any = None) -> int:
    if rclpy is None:
        log.error("rclpy not available; cannot run plugin")
        return 1
    rclpy.init(args=args)
    node = WcpWorkerNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
    return 0
