"""
VDA 5050 capability declaration for the WCP adapter.

Derives a WCP CapabilityDescriptor from a VDA 5050 Factsheet message.

VDA 5050 Factsheet (msg type 5) fields used:
- agvGeometry.wheelDefinitions, footprint
- loadSpecification.loadSets[], maxWeight
- physicalParameters.speedMin, speedMax, accelerationMax, decelerationMax
- agvKinematic ("DIFF", "OMNI", "THREEWHEEL", ...)
- typeSpecification.agvKinematic, agvClass

References:
- VDA 5050 v2.0.0 specification
- RFC 0024 (VDA 5050 adapter design)
"""
from __future__ import annotations

from typing import Any


def factsheet_to_class_extension(factsheet: dict[str, Any]) -> dict[str, Any]:
    """Translate a VDA 5050 Factsheet message into a WCP class_extension.

    The function is tolerant of partial factsheets; missing fields drop
    out of the result rather than raising.
    """
    ext: dict[str, Any] = {"platform": "ground_amr", "vda5050_version": "2.0.0"}

    ts = factsheet.get("typeSpecification", {})
    if ts:
        ext["agv_class"] = ts.get("agvClass")
        ext["agv_kinematic"] = ts.get("agvKinematic")
        ext["max_load_mass_kg"] = ts.get("maxLoadMass")
        ext["localization_types"] = ts.get("localizationTypes")
        ext["navigation_types"] = ts.get("navigationTypes")

    pp = factsheet.get("physicalParameters", {})
    if pp:
        ext["speed_min_mps"] = pp.get("speedMin")
        ext["speed_max_mps"] = pp.get("speedMax")
        ext["acceleration_max_mps2"] = pp.get("accelerationMax")
        ext["deceleration_max_mps2"] = pp.get("decelerationMax")
        ext["height_min_m"] = pp.get("heightMin")
        ext["height_max_m"] = pp.get("heightMax")
        ext["width_m"] = pp.get("width")
        ext["length_m"] = pp.get("length")

    ls = factsheet.get("loadSpecification", {})
    if ls:
        ext["load_positions"] = ls.get("loadPositions")
        ext["load_sets"] = [
            {
                "name": s.get("setName"),
                "load_type": s.get("loadType"),
                "max_weight_kg": s.get("maxWeight"),
            }
            for s in ls.get("loadSets", [])
        ]

    return ext


def build_capability_descriptor(
    *,
    worker_did: str,
    coordinator_did: str,
    adapter_signer_key_id: str,
    adapter_pubkey_multibase: str,
    factsheet: dict[str, Any],
    trust_class: str = "software-keypair",
) -> dict[str, Any]:
    """Construct a CapabilityDescriptor for a VDA 5050-bridged AMR."""
    return {
        "schema_version": "wcp/1.0-rc1",
        "did": worker_did,
        "worker_class": "autonomous_robot",
        "coordinator_did": coordinator_did,
        "descriptor_types_supported": [
            "transport",  # the canonical pallet/load move
            "pickup_dropoff",
        ],
        "class_extension": factsheet_to_class_extension(factsheet),
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
            "indoor_pose_track",
            "weight_delta",
            "iot_beacon_proximity",
            "vda5050_order_log",
        ],
        "connectivity_profile": "continuous",
    }
