"""
VDA 5050-to-WCP bridge.

Runs as a WCP worker that subscribes to a VDA 5050 fleet's MQTT topics
and exposes one or more AMRs as WCP workers. Implements RFC 0024.

VDA 5050 topic conventions used here (matching v2.0.0):

    {interfaceName}/{majorVersion}/{manufacturer}/{serialNumber}/order
    {interfaceName}/{majorVersion}/{manufacturer}/{serialNumber}/instantActions
    {interfaceName}/{majorVersion}/{manufacturer}/{serialNumber}/state
    {interfaceName}/{majorVersion}/{manufacturer}/{serialNumber}/visualization
    {interfaceName}/{majorVersion}/{manufacturer}/{serialNumber}/factsheet
    {interfaceName}/{majorVersion}/{manufacturer}/{serialNumber}/connection

The bridge does NOT speak directly to the AMR hardware; it speaks to the
broker the AMR is already subscribed to.

Per RFC 0024, this is the v1.1 reference adapter and lives under
examples/adapters/ rather than the planned examples/vda5050-bridge/.
"""
from __future__ import annotations

import asyncio
import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional, Protocol

from wcp_sdk.types import AttestationMode
from wcp_sdk.v2 import Worker

from . import capability as cap_mod


class MQTTClient(Protocol):
    """Minimal async MQTT surface (paho-mqtt or asyncio-mqtt-compatible)."""

    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...
    async def subscribe(self, topic: str) -> None: ...
    async def publish(self, topic: str, payload: bytes, qos: int = 1) -> None: ...
    async def messages(self) -> "asyncio.Queue[tuple[str, bytes]]": ...


@dataclass
class VDA5050BridgeConfig:
    coordinator_url: str = "ws://localhost:8000/wcp/ws"
    broker_url: str = "mqtt://localhost:1883"
    interface_name: str = "uagv"
    major_version: str = "v2"
    manufacturer: str = "example-fleet-vendor"
    serial_number: str = "amr-001"
    worker_did: str = "did:wcp:example-vda5050-amr-001"
    coordinator_did: str = "did:wcp:example-coordinator"
    adapter_signer_key_id: str = "k1"
    adapter_pubkey_multibase: str = "z6Mk-EXAMPLE-vda5050-pubkey"


@dataclass
class _OrderState:
    """Tracks one in-flight VDA 5050 Order corresponding to a WCP claim."""

    claim_id: str
    order_id: str
    order_update_id: int = 0
    state_log: list[dict[str, Any]] = field(default_factory=list)
    last_position: Optional[dict[str, Any]] = None
    completed: asyncio.Event = field(default_factory=asyncio.Event)


def wcp_transport_to_vda5050_order(
    descriptor_payload: dict[str, Any],
    *,
    order_id: str,
    order_update_id: int = 0,
) -> dict[str, Any]:
    """Translate a WCP transport descriptor_payload into a VDA 5050 Order.

    Expected descriptor_payload shape (matching `examples/agents/logistics/agent.py`):

        {
            "pickup": "<node_id>",
            "dropoff": "<node_id>",
            "payload_description": "...",
            "handoff_protocol": "..."
        }

    The Order built here is the minimum viable two-node route:
    pickup node -> edge -> dropoff node. A production translator would
    invoke the fleet's path planner to produce the full set of nodes and
    edges; pure two-node orders only work where the fleet's local
    autonomy is able to route between the named nodes.
    """
    now = datetime.now(timezone.utc).isoformat()
    pickup_node = descriptor_payload["pickup"]
    dropoff_node = descriptor_payload["dropoff"]
    return {
        "headerId": 0,
        "timestamp": now,
        "version": "2.0.0",
        "manufacturer": "wcp-vda5050-bridge",
        "serialNumber": "bridge",
        "orderId": order_id,
        "orderUpdateId": order_update_id,
        "nodes": [
            {
                "nodeId": pickup_node,
                "sequenceId": 0,
                "released": True,
                "nodePosition": None,
                "actions": [
                    {
                        "actionId": f"pick-{uuid.uuid4().hex[:8]}",
                        "actionType": "pick",
                        "blockingType": "HARD",
                        "actionParameters": [
                            {
                                "key": "loadType",
                                "value": descriptor_payload.get(
                                    "load_type", "PALLET_EUR1"
                                ),
                            }
                        ],
                    }
                ],
            },
            {
                "nodeId": dropoff_node,
                "sequenceId": 2,
                "released": True,
                "nodePosition": None,
                "actions": [
                    {
                        "actionId": f"drop-{uuid.uuid4().hex[:8]}",
                        "actionType": "drop",
                        "blockingType": "HARD",
                        "actionParameters": [],
                    }
                ],
            },
        ],
        "edges": [
            {
                "edgeId": f"e-{pickup_node}-{dropoff_node}",
                "sequenceId": 1,
                "released": True,
                "startNodeId": pickup_node,
                "endNodeId": dropoff_node,
                "actions": [],
            }
        ],
    }


def vda5050_state_to_attestation_payload(
    state_log: list[dict[str, Any]],
) -> dict[str, Any]:
    """Convert accumulated VDA 5050 State messages into a WCP audit payload."""
    samples = []
    for s in state_log:
        agv_pos = s.get("agvPosition") or {}
        samples.append(
            {
                "t": s.get("timestamp"),
                "x": agv_pos.get("x"),
                "y": agv_pos.get("y"),
                "theta": agv_pos.get("theta"),
                "map_id": agv_pos.get("mapId"),
                "last_node_id": s.get("lastNodeId"),
            }
        )
    return {
        "kind": "indoor_pose_track",
        "payload": {"track": samples, "sample_count": len(samples)},
    }


class VDA5050Bridge:
    """The WCP worker process bridging to one VDA 5050 AMR."""

    def __init__(
        self,
        config: VDA5050BridgeConfig,
        mqtt: MQTTClient,
        factsheet: dict[str, Any],
    ) -> None:
        self.cfg = config
        self.mqtt = mqtt
        self.factsheet = factsheet
        self.worker = Worker(
            name="vda5050-bridge",
            worker_class="autonomous_robot",
            coordinator=config.coordinator_url,
        )
        self._orders: dict[str, _OrderState] = {}  # claim_id -> _OrderState
        self._wire_handlers()

    def _topic(self, leaf: str) -> str:
        c = self.cfg
        return f"{c.interface_name}/{c.major_version}/{c.manufacturer}/{c.serial_number}/{leaf}"

    def _wire_handlers(self) -> None:
        worker = self.worker
        bridge = self

        @worker.capability(
            descriptor_types=["transport", "pickup_dropoff"],
            class_extension=cap_mod.factsheet_to_class_extension(self.factsheet),
        )
        def declare() -> None:
            return None

        @worker.handle("transport")
        @worker.handle("pickup_dropoff")
        async def execute(task: dict) -> dict:
            claim_id = task["claim_id"]
            order_id = f"wcp-{claim_id}"
            order = wcp_transport_to_vda5050_order(
                task.get("descriptor_payload", {}),
                order_id=order_id,
            )
            state = _OrderState(claim_id=claim_id, order_id=order_id)
            bridge._orders[claim_id] = state

            await bridge.mqtt.publish(
                bridge._topic("order"),
                json.dumps(order).encode("utf-8"),
                qos=1,
            )

            # Wait for the AMR to report orderId completion via state
            await asyncio.wait_for(state.completed.wait(), timeout=3600)

            return {
                "vda5050_order_id": order_id,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "state_samples": len(state.state_log),
            }

        @worker.attest(AttestationMode.SENSOR_WITNESS)
        async def attest_pose(claim_id: str, task: dict) -> dict:
            order = bridge._orders.get(claim_id)
            if order is None:
                return {"kind": "indoor_pose_track", "payload": {"track": []}}
            return vda5050_state_to_attestation_payload(order.state_log)

    async def watch_state_topic(self) -> None:
        """Consume VDA 5050 state messages and route to the matching order."""
        await self.mqtt.subscribe(self._topic("state"))
        q = await self.mqtt.messages()
        while True:
            topic, payload = await q.get()
            if topic != self._topic("state"):
                continue
            try:
                msg = json.loads(payload)
            except json.JSONDecodeError:
                continue
            order_id = msg.get("orderId")
            for o in self._orders.values():
                if o.order_id == order_id:
                    o.state_log.append(msg)
                    # VDA 5050 spec: orderId only present while order is
                    # active; cleared once complete. A more robust check
                    # examines lastNodeId == final node + nodeStates empty.
                    if not msg.get("nodeStates") and not msg.get("edgeStates"):
                        o.completed.set()
                    break

    async def run(self) -> None:
        await self.mqtt.connect()
        try:
            asyncio.create_task(self.watch_state_topic())
            await asyncio.to_thread(self.worker.run)
        finally:
            await self.mqtt.disconnect()


def main() -> None:
    cfg = VDA5050BridgeConfig(
        coordinator_url=os.environ.get(
            "WCP_COORDINATOR", "ws://localhost:8000/wcp/ws"
        ),
        broker_url=os.environ.get("VDA5050_BROKER", "mqtt://localhost:1883"),
    )
    raise SystemExit(
        "Wire an MQTTClient implementation (e.g., asyncio-mqtt) and pass "
        "the AMR's factsheet (or a stub) to VDA5050Bridge(cfg, mqtt, fs). "
        "See README.md for the suggested setup."
    )


if __name__ == "__main__":
    main()
