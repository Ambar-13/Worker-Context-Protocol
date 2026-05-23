"""
Vendor robot bridge: capability declaration template.

This template assumes the vendor SDK exposes some form of "robot info"
call that returns kinematics, payload, sensors, and a list of supported
operations. Fill in the TODOs below from your vendor's actual SDK shape.
"""
from __future__ import annotations

from typing import Any


def vendor_info_to_class_extension(vendor_info: dict[str, Any]) -> dict[str, Any]:
    """Translate a vendor info dict into a WCP class_extension.

    TODO: Replace this with the real translation for your vendor's SDK.
    The keys below are illustrative; rename them to match what your
    vendor's robot info call actually returns.
    """
    return {
        "platform": "vendor_specific",
        "vendor": vendor_info.get("vendor", "unknown"),
        "model": vendor_info.get("model", "unknown"),
        "serial": vendor_info.get("serial"),
        # TODO: kinematics (joints, dof, payload, reach)
        "dof": vendor_info.get("dof"),
        "max_payload_kg": vendor_info.get("max_payload_kg"),
        # TODO: sensors (cameras, force-torque, etc.)
        "sensors": vendor_info.get("sensors", []),
        # TODO: supported operations
        "operations_supported": vendor_info.get(
            "operations_supported", []
        ),
    }


def build_capability_descriptor(
    *,
    worker_did: str,
    coordinator_did: str,
    adapter_signer_key_id: str,
    adapter_pubkey_multibase: str,
    vendor_info: dict[str, Any],
    descriptor_types: list[str],
    attestation_kinds: list[str],
    trust_class: str = "software-keypair",
    connectivity_profile: str = "continuous",
) -> dict[str, Any]:
    """Construct a CapabilityDescriptor for a vendor-bridged robot."""
    return {
        "schema_version": "wcp/0.2",
        "did": worker_did,
        "worker_class": "autonomous_robot",  # TODO: or teleoperated_system, hybrid_human_robot
        "coordinator_did": coordinator_did,
        "descriptor_types_supported": descriptor_types,
        "class_extension": vendor_info_to_class_extension(vendor_info),
        "attestation_keys": [
            {
                "key_id": adapter_signer_key_id,
                "did": worker_did,
                "public_key_multibase": adapter_pubkey_multibase,
                "algorithm": "Ed25519",
                "trust_class": trust_class,
            }
        ],
        "attestation_kinds_produced": attestation_kinds,
        "connectivity_profile": connectivity_profile,
    }
