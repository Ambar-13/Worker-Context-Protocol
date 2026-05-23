"""
ROS 1 to WCP bridge.

Runs as a WCP worker that connects to a ROS 1 master, subscribes to
topics, calls services, and dispatches actionlib goals on demand.

Deployment topology:

    WCP coordinator <--WCP--> this bridge <--ROS 1 client--> roscore <--> ROS nodes

The bridge uses the standard ROS 1 client library (rospy) on the ROS
side. For ROS 2 native deployments, see the `wcp_worker` ROS 2 plugin
package shipped separately.

The bridge accepts ROS-shaped tasks where the descriptor_type names a
ROS action or service the operator's profile has exposed. The
descriptor_payload contains the action goal or service request.
"""
from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Protocol

from wcp_sdk.types import AttestationMode
from wcp_sdk.v2 import Worker

from . import capability as cap_mod


class ROS1Client(Protocol):
    """Async wrapper around rospy.

    Concrete implementations bridge async/await onto rospy's threading
    model (which is what `ros1_bridge` does internally for ROS 2 today).
    """

    def init_node(self, name: str) -> None: ...

    async def subscribe_topic(
        self, topic: str, msg_type: str
    ) -> "asyncio.Queue[dict[str, Any]]": ...

    async def call_service(
        self, service: str, srv_type: str, request: dict[str, Any]
    ) -> dict[str, Any]: ...

    async def send_action_goal(
        self, action: str, action_type: str, goal: dict[str, Any]
    ) -> dict[str, Any]: ...


@dataclass
class ROS1BridgeConfig:
    coordinator_url: str = "ws://localhost:8000/wcp/ws"
    ros_master_uri: str = "http://localhost:11311"
    bridge_node_name: str = "wcp_ros1_bridge"
    worker_did: str = "did:wcp:example-ros1-robot-001"
    coordinator_did: str = "did:wcp:example-coordinator"
    adapter_signer_key_id: str = "k1"
    adapter_pubkey_multibase: str = "z6Mk-EXAMPLE-ros1-pubkey"


@dataclass
class _TopicSampleLog:
    claim_id: str
    topic: str
    msg_type: str
    samples: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class _ActionResult:
    claim_id: str
    action: str
    result: Optional[dict[str, Any]] = None
    started_at: str = ""
    finished_at: str = ""


class ROS1Bridge:
    """WCP worker that bridges to one ROS 1 master."""

    def __init__(
        self,
        config: ROS1BridgeConfig,
        ros: ROS1Client,
        profile: dict[str, Any],
    ) -> None:
        self.cfg = config
        self.ros = ros
        self.profile = profile
        self.worker = Worker(
            name="ros1-bridge",
            worker_class="autonomous_robot",
            coordinator=config.coordinator_url,
        )
        self._action_results: dict[str, _ActionResult] = {}
        self._topic_logs: dict[str, _TopicSampleLog] = {}
        self._wire_handlers()

    def _wire_handlers(self) -> None:
        worker = self.worker
        bridge = self
        profile = self.profile
        actions = profile.get("action_map", {}) or {}
        services = profile.get("service_map", {}) or {}

        @worker.capability(
            descriptor_types=sorted(actions.keys() | services.keys())
            or ["ros1_generic_task"],
            class_extension=cap_mod.ros1_profile_to_class_extension(profile),
        )
        def declare() -> None:
            return None

        for action_name, action_def in actions.items():
            @worker.handle(action_name)  # type: ignore[misc]
            async def execute_action(
                task: dict, _a=action_name, _d=action_def,
            ) -> dict:
                claim_id = task["claim_id"]
                started = datetime.now(timezone.utc).isoformat()
                # Optionally subscribe to a progress topic during the goal
                progress_topic = _d.get("progress_topic")
                log: Optional[_TopicSampleLog] = None
                progress_task: Optional[asyncio.Task] = None
                if progress_topic:
                    log = _TopicSampleLog(
                        claim_id=claim_id,
                        topic=progress_topic,
                        msg_type=_d.get("progress_msg_type", "unknown"),
                    )
                    bridge._topic_logs[claim_id] = log
                    progress_task = asyncio.create_task(
                        bridge._drain_topic(log)
                    )
                try:
                    result = await bridge.ros.send_action_goal(
                        _d["action"],
                        _d["action_type"],
                        task.get("descriptor_payload", {}),
                    )
                finally:
                    if progress_task is not None:
                        progress_task.cancel()
                finished = datetime.now(timezone.utc).isoformat()
                bridge._action_results[claim_id] = _ActionResult(
                    claim_id=claim_id,
                    action=_a,
                    result=result,
                    started_at=started,
                    finished_at=finished,
                )
                return {
                    "action": _a,
                    "started_at": started,
                    "finished_at": finished,
                    "result_summary": result.get("status", "succeeded"),
                }

        for svc_name, svc_def in services.items():
            @worker.handle(svc_name)  # type: ignore[misc]
            async def execute_service(
                task: dict, _n=svc_name, _d=svc_def,
            ) -> dict:
                claim_id = task["claim_id"]
                response = await bridge.ros.call_service(
                    _d["service"],
                    _d["srv_type"],
                    task.get("descriptor_payload", {}),
                )
                bridge._action_results[claim_id] = _ActionResult(
                    claim_id=claim_id,
                    action=_n,
                    result=response,
                    started_at=datetime.now(timezone.utc).isoformat(),
                    finished_at=datetime.now(timezone.utc).isoformat(),
                )
                return {"service": _n, "response_summary_keys": sorted(response)}

        @worker.attest(AttestationMode.SENSOR_WITNESS)
        async def attest_action(claim_id: str, task: dict) -> dict:
            log = bridge._topic_logs.get(claim_id)
            if log is not None and log.samples:
                return {
                    "kind": "ros1_topic_sample_log",
                    "payload": {
                        "topic": log.topic,
                        "msg_type": log.msg_type,
                        "samples": log.samples,
                    },
                }
            res = bridge._action_results.get(claim_id)
            if res is not None:
                return {
                    "kind": "ros1_action_result"
                    if res.action in (profile.get("action_map") or {})
                    else "ros1_service_call_result",
                    "payload": {
                        "name": res.action,
                        "started_at": res.started_at,
                        "finished_at": res.finished_at,
                        "result": res.result,
                    },
                }
            return {"kind": "ros1_action_result", "payload": {"result": None}}

    async def _drain_topic(self, log: _TopicSampleLog) -> None:
        q = await self.ros.subscribe_topic(log.topic, log.msg_type)
        while True:
            msg = await q.get()
            log.samples.append(
                {"t": datetime.now(timezone.utc).isoformat(), "msg": msg}
            )

    async def run(self) -> None:
        self.ros.init_node(self.cfg.bridge_node_name)
        await asyncio.to_thread(self.worker.run)


def main() -> None:
    cfg = ROS1BridgeConfig(
        coordinator_url=os.environ.get(
            "WCP_COORDINATOR", "ws://localhost:8000/wcp/ws"
        ),
        ros_master_uri=os.environ.get(
            "ROS_MASTER_URI", "http://localhost:11311"
        ),
    )
    raise SystemExit(
        "Wire a ROS1Client implementation (e.g., a thin rospy wrapper) "
        "and a profile dict; then run ROS1Bridge(cfg, client, profile).run()."
    )


if __name__ == "__main__":
    main()
