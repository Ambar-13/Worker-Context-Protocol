"""
Modbus PLC capability declaration for the WCP adapter.

Modbus has no Factsheet equivalent; capability for a Modbus device comes
from the operator's register map, configured at deployment time. The
adapter accepts a `register_map` dict and translates it into a WCP
class_extension. The class_extension exposes:

- `input_registers` and `holding_registers` summary (count, address ranges)
- `commands_supported` (each command is a named, parametrized write to one
  or more holding registers; the operator defines these in the register map)
- `read_kinds_produced` (each is a named, periodic read that becomes
  evidence of operation)
"""
from __future__ import annotations

from typing import Any


def register_map_to_class_extension(
    register_map: dict[str, Any],
) -> dict[str, Any]:
    """Translate a register-map dict into a WCP class_extension block.

    Expected register_map shape:

        {
            "device_class": "valve_actuator" | "pump_controller" | "smart_meter" | "generic",
            "modbus_unit_id": 1,
            "input_registers": [
                {"name": "flow_rate_lpm", "address": 30001, "scale": 0.1},
                ...
            ],
            "holding_registers": [
                {"name": "setpoint_lpm", "address": 40001, "scale": 0.1, "writable": true},
                ...
            ],
            "coils": [
                {"name": "main_valve_open", "address": 1, "writable": true},
                ...
            ],
            "commands": {
                "open_valve_to_pct": {"register": "setpoint_lpm", "kind": "scaled_uint16"},
                "emergency_close": {"coil": "main_valve_open", "value": false}
            }
        }
    """
    inputs = register_map.get("input_registers", []) or []
    holdings = register_map.get("holding_registers", []) or []
    coils = register_map.get("coils", []) or []

    return {
        "platform": "industrial_io",
        "protocol": "modbus_tcp",
        "device_class": register_map.get("device_class", "generic"),
        "modbus_unit_id": register_map.get("modbus_unit_id", 1),
        "input_register_count": len(inputs),
        "holding_register_count": len(holdings),
        "coil_count": len(coils),
        "named_signals_read": sorted(
            [r["name"] for r in inputs] + [r["name"] for r in holdings]
        ),
        "named_signals_write": sorted(
            [r["name"] for r in holdings if r.get("writable")]
            + [c["name"] for c in coils if c.get("writable")]
        ),
        "commands_supported": sorted(register_map.get("commands", {}).keys()),
    }


def build_capability_descriptor(
    *,
    worker_did: str,
    coordinator_did: str,
    adapter_signer_key_id: str,
    adapter_pubkey_multibase: str,
    register_map: dict[str, Any],
    trust_class: str = "software-keypair",
) -> dict[str, Any]:
    """Construct a CapabilityDescriptor for a Modbus-bridged PLC."""
    return {
        "schema_version": "wcp/1.0-rc1",
        "did": worker_did,
        "worker_class": "autonomous_robot",
        "coordinator_did": coordinator_did,
        "descriptor_types_supported": ["plc_command", "plc_read_window"],
        "class_extension": register_map_to_class_extension(register_map),
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
            "plc_register_read_window",
            "plc_command_acknowledgement",
        ],
        "connectivity_profile": "continuous",
    }
