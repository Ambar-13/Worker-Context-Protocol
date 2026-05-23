"""
MQTT IoT capability declaration for the WCP adapter.

For an MQTT-attached sensor fleet, capability comes from the operator's
*topic map*: a declaration of which topics carry which named sensor
streams, what payload schema each stream uses, and which (if any) topics
accept commands.
"""
from __future__ import annotations

from typing import Any


def topic_map_to_class_extension(topic_map: dict[str, Any]) -> dict[str, Any]:
    """Translate a topic-map dict into a WCP class_extension block.

    Expected topic_map shape:

        {
            "device_class": "weather_station" | "soil_sensor" | "air_quality" | "generic",
            "device_count": 12,
            "sensor_streams": [
                {
                    "name": "temperature_c",
                    "topic": "field/+/temp",
                    "payload_schema": "scalar_float",
                    "rate_hz_approx": 0.1
                },
                ...
            ],
            "command_topics": [
                {"name": "request_reading", "topic": "field/+/cmd/read", "payload_schema": "trigger"}
            ]
        }
    """
    streams = topic_map.get("sensor_streams", []) or []
    cmds = topic_map.get("command_topics", []) or []
    return {
        "platform": "iot_sensor_fleet",
        "protocol": "mqtt_v5",
        "device_class": topic_map.get("device_class", "generic"),
        "device_count": topic_map.get("device_count"),
        "sensor_stream_count": len(streams),
        "sensor_streams": [
            {
                "name": s["name"],
                "payload_schema": s.get("payload_schema"),
                "rate_hz_approx": s.get("rate_hz_approx"),
            }
            for s in streams
        ],
        "command_topics_supported": [c["name"] for c in cmds],
    }


def build_capability_descriptor(
    *,
    worker_did: str,
    coordinator_did: str,
    adapter_signer_key_id: str,
    adapter_pubkey_multibase: str,
    topic_map: dict[str, Any],
    trust_class: str = "software-keypair",
) -> dict[str, Any]:
    """Construct a CapabilityDescriptor for an MQTT-bridged sensor fleet."""
    return {
        "schema_version": "wcp/1.0-rc1",
        "did": worker_did,
        "worker_class": "autonomous_robot",
        "coordinator_did": coordinator_did,
        "descriptor_types_supported": [
            "sensor_read_window",
            "sensor_trigger_capture",
        ],
        "class_extension": topic_map_to_class_extension(topic_map),
        "attestation_keys": [
            {
                "key_id": adapter_signer_key_id,
                "did": worker_did,
                "public_key_multibase": adapter_pubkey_multibase,
                "algorithm": "Ed25519",
                "trust_class": trust_class,
            }
        ],
        "attestation_kinds_produced": [
            "mqtt_sensor_window",
            "mqtt_capture_manifest",
        ],
        "connectivity_profile": "continuous",
    }
