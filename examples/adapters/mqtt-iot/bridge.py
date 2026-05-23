"""
MQTT-to-WCP bridge.

Runs as a WCP worker that subscribes to an MQTT broker and exposes a
fleet of MQTT-attached sensors (or actuators) as a single WCP worker.

The bridge accepts:
- `sensor_read_window` tasks: subscribe to a set of named streams for a
  fixed window and aggregate samples into evidence
- `sensor_trigger_capture` tasks: publish a trigger command to a named
  command topic and capture the resulting response stream

A typical deployment fronts a single MQTT broker (Mosquitto, EMQX, HiveMQ)
that already has many sensor devices reporting to it. The bridge does
NOT provision devices or run the broker; both are operator-managed.
"""
from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Protocol

from wcp_sdk.types import AttestationMode
from wcp_sdk.v2 import Worker

from . import capability as cap_mod


class MQTTClient(Protocol):
    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...
    async def subscribe(self, topic: str) -> None: ...
    async def publish(self, topic: str, payload: bytes, qos: int = 1) -> None: ...
    async def messages(self) -> "asyncio.Queue[tuple[str, bytes]]": ...


@dataclass
class MQTTBridgeConfig:
    coordinator_url: str = "ws://localhost:8000/wcp/ws"
    broker_url: str = "mqtt://localhost:1883"
    worker_did: str = "did:wcp:example-mqtt-iot-fleet-001"
    coordinator_did: str = "did:wcp:example-coordinator"
    adapter_signer_key_id: str = "k1"
    adapter_pubkey_multibase: str = "z6Mk-EXAMPLE-mqtt-pubkey"


@dataclass
class _ReadWindowRecord:
    claim_id: str
    streams: list[str]
    samples: list[dict[str, Any]] = field(default_factory=list)
    end_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


def _decode_payload(payload: bytes, schema: str | None) -> Any:
    """Decode an MQTT payload per its declared schema.

    Supported:
        scalar_float / scalar_int / scalar_bool / scalar_string
        json (parsed as application/json)
        trigger (empty body or any body; treated as "fired")
    """
    if schema == "json":
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            return None
    if schema == "scalar_float":
        try:
            return float(payload.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return None
    if schema == "scalar_int":
        try:
            return int(payload.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return None
    if schema == "scalar_bool":
        try:
            return payload.decode("utf-8").strip().lower() in (
                "1", "true", "yes", "on"
            )
        except UnicodeDecodeError:
            return None
    if schema == "scalar_string":
        try:
            return payload.decode("utf-8")
        except UnicodeDecodeError:
            return None
    if schema == "trigger":
        return "fired"
    # Default: hex of raw bytes
    return payload.hex()


class MQTTBridge:
    """WCP worker for an MQTT-attached sensor/actuator fleet."""

    def __init__(
        self,
        config: MQTTBridgeConfig,
        mqtt: MQTTClient,
        topic_map: dict[str, Any],
    ) -> None:
        self.cfg = config
        self.mqtt = mqtt
        self.topic_map = topic_map
        self.worker = Worker(
            name="mqtt-iot-bridge",
            worker_class="autonomous_robot",
            coordinator=config.coordinator_url,
        )
        self._reads: dict[str, _ReadWindowRecord] = {}
        self._stream_index: dict[str, dict[str, Any]] = {
            s["name"]: s
            for s in topic_map.get("sensor_streams", []) or []
        }
        self._command_index: dict[str, dict[str, Any]] = {
            c["name"]: c
            for c in topic_map.get("command_topics", []) or []
        }
        self._wire_handlers()

    def _matches_topic_filter(self, mqtt_topic: str, sub_filter: str) -> bool:
        # Minimal MQTT topic filter implementation (handles + and #)
        if sub_filter == mqtt_topic:
            return True
        sf = sub_filter.split("/")
        mt = mqtt_topic.split("/")
        i = 0
        for tok in sf:
            if tok == "#":
                return True
            if i >= len(mt):
                return False
            if tok == "+" or tok == mt[i]:
                i += 1
                continue
            return False
        return i == len(mt)

    def _wire_handlers(self) -> None:
        worker = self.worker
        bridge = self

        @worker.capability(
            descriptor_types=[
                "sensor_read_window",
                "sensor_trigger_capture",
            ],
            class_extension=cap_mod.topic_map_to_class_extension(self.topic_map),
        )
        def declare() -> None:
            return None

        @worker.handle("sensor_read_window")
        async def execute_read_window(task: dict) -> dict:
            claim_id = task["claim_id"]
            payload = task.get("descriptor_payload", {})
            streams = list(payload.get("streams", []))
            window_s = float(payload.get("window_seconds", 60))
            rec = _ReadWindowRecord(
                claim_id=claim_id,
                streams=streams,
                end_at=datetime.now(timezone.utc)
                + timedelta(seconds=window_s),
            )
            bridge._reads[claim_id] = rec
            # Subscribe to all streams
            for s in streams:
                sdef = bridge._stream_index.get(s)
                if sdef is None:
                    continue
                await bridge.mqtt.subscribe(sdef["topic"])
            await asyncio.sleep(window_s)
            return {
                "window_seconds": window_s,
                "sample_count": len(rec.samples),
            }

        @worker.handle("sensor_trigger_capture")
        async def execute_trigger(task: dict) -> dict:
            payload = task.get("descriptor_payload", {})
            cmd_name = payload["command"]
            cdef = bridge._command_index.get(cmd_name)
            if cdef is None:
                raise KeyError(f"command {cmd_name!r} not in topic map")
            body = json.dumps(payload.get("body", {})).encode("utf-8")
            await bridge.mqtt.publish(cdef["topic"], body, qos=1)
            return {
                "published": cdef["topic"],
                "at": datetime.now(timezone.utc).isoformat(),
            }

        @worker.attest(AttestationMode.SENSOR_WITNESS)
        async def attest_window(claim_id: str, task: dict) -> dict:
            rec = bridge._reads.get(claim_id)
            if rec is None:
                return {"kind": "mqtt_sensor_window", "payload": {"samples": []}}
            return {
                "kind": "mqtt_sensor_window",
                "payload": {
                    "streams": rec.streams,
                    "samples": rec.samples,
                },
            }

    async def consume_messages(self) -> None:
        """Forward incoming MQTT messages into the active read windows."""
        q = await self.mqtt.messages()
        while True:
            topic, payload = await q.get()
            now = datetime.now(timezone.utc)
            # Match topic against each stream filter
            for s_name, s_def in self._stream_index.items():
                if not self._matches_topic_filter(topic, s_def["topic"]):
                    continue
                value = _decode_payload(payload, s_def.get("payload_schema"))
                sample = {
                    "t": now.isoformat(),
                    "stream": s_name,
                    "topic": topic,
                    "value": value,
                }
                for rec in self._reads.values():
                    if s_name in rec.streams and now <= rec.end_at:
                        rec.samples.append(sample)

    async def run(self) -> None:
        await self.mqtt.connect()
        try:
            asyncio.create_task(self.consume_messages())
            await asyncio.to_thread(self.worker.run)
        finally:
            await self.mqtt.disconnect()


def main() -> None:
    cfg = MQTTBridgeConfig(
        coordinator_url=os.environ.get(
            "WCP_COORDINATOR", "ws://localhost:8000/wcp/ws"
        ),
        broker_url=os.environ.get("MQTT_BROKER", "mqtt://localhost:1883"),
    )
    raise SystemExit(
        "Wire an MQTTClient implementation (e.g., asyncio-mqtt) and a "
        "topic-map dict, then run MQTTBridge(cfg, mqtt, tm).run()."
    )


if __name__ == "__main__":
    main()
