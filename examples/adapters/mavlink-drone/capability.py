"""
MAVLink drone capability declaration for the WCP adapter.

Translates a vehicle's MAVLink autopilot identity, parameter values, and
extended status into a WCP CapabilityDescriptor.

Reference fields drawn from MAVLink common-message and PX4/ArduPilot
parameter conventions:

- AUTOPILOT_VERSION.flight_sw_version, capabilities, vendor_id
- HEARTBEAT.type (MAV_TYPE_QUADROTOR, MAV_TYPE_HEXAROTOR, etc.)
- PARAM (LANDING_GEAR, FENCE_TYPE, BATT*_CAPACITY, etc.)
- COMMAND_LONG flight modes the vehicle reports as supported

The values used below are placeholder defaults for a generic small
quadrotor; production adapters should populate from live MAVLink reads.
"""
from __future__ import annotations

from typing import Any


def mavlink_type_to_wcp_class_extension(
    mav_type: str,
    *,
    battery_capacity_mah: int,
    max_payload_kg: float,
    max_endurance_minutes: float,
    max_range_km: float,
    sensors: list[str],
) -> dict[str, Any]:
    """Map a MAV_TYPE label into a WCP class_extension block.

    Args:
        mav_type: human label like "quadrotor", "hexarotor", "fixed_wing"
        battery_capacity_mah: PARAM BATT*_CAPACITY in milliamp-hours
        max_payload_kg: vehicle-rated payload
        max_endurance_minutes: typical flight time at hover with no payload
        max_range_km: line-of-sight range under nominal conditions
        sensors: list of onboard sensors that produce evidence-grade output
    """
    return {
        "platform": "aerial",
        "mav_type": mav_type,
        "battery_capacity_mah": battery_capacity_mah,
        "max_payload_kg": max_payload_kg,
        "max_endurance_minutes": max_endurance_minutes,
        "max_range_km": max_range_km,
        "sensors": sensors,
        "autopilot": "mavlink-2.0",
        "gnss_fix_required": True,
    }


def build_capability_descriptor(
    *,
    worker_did: str,
    coordinator_did: str,
    adapter_signer_key_id: str,
    adapter_pubkey_multibase: str,
    mav_type: str = "quadrotor",
    battery_capacity_mah: int = 5200,
    max_payload_kg: float = 2.0,
    max_endurance_minutes: float = 28.0,
    max_range_km: float = 8.0,
    sensors: tuple[str, ...] = ("rgb_camera_4k", "thermal_640", "gnss_l1l5"),
    trust_class: str = "software-keypair",
) -> dict[str, Any]:
    """Construct a CapabilityDescriptor for a MAVLink-bridged drone.

    Notes:
        - The adapter's key signs evidence on the vehicle's behalf. The
          device itself does NOT directly produce WCP signatures; its
          autopilot has no notion of WCP DIDs.
        - `connectivity_profile = "intermittent"` because aerial workers
          frequently lose link during low-altitude or beyond-line-of-sight
          flight; RFC 0029 buffer-and-replay applies.
    """
    return {
        "schema_version": "wcp/1.0-rc1",
        "did": worker_did,
        "worker_class": "autonomous_robot",
        "coordinator_did": coordinator_did,
        "descriptor_types_supported": [
            "aerial_inspection",
            "aerial_survey",
            "aerial_delivery_lite",
        ],
        "class_extension": mavlink_type_to_wcp_class_extension(
            mav_type=mav_type,
            battery_capacity_mah=battery_capacity_mah,
            max_payload_kg=max_payload_kg,
            max_endurance_minutes=max_endurance_minutes,
            max_range_km=max_range_km,
            sensors=list(sensors),
        ),
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
            "geo_track",
            "barometric_altitude_profile",
            "image_capture_manifest",
            "thermal_capture_manifest",
        ],
        "connectivity_profile": "intermittent",
        "max_offline_duration_seconds": 900,
        "buffer_capacity_audit_entries": 2048,
    }
