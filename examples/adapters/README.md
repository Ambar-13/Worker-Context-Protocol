# WCP Adapter Examples

This directory contains reference adapter implementations that bridge existing robotics, automation, and IoT protocols to WCP. An adapter exposes a non-WCP-native device (a MAVLink drone, a VDA 5050 AMR, a Modbus PLC, an MQTT-attached sensor, a ROS 1 robot, etc.) as a WCP worker without requiring a firmware change to the underlying device.

## What an adapter is (and isn't)

An adapter is a small process (typically a single host or a sidecar container) that:

1. Speaks the native protocol of one or more devices on its south-bound side
2. Speaks WCP JSON-RPC-over-WebSocket on its north-bound side (to the coordinator)
3. Translates capability declarations, task descriptors, execution status, and attestation evidence between the two

An adapter is NOT:

- A real-time controller. Real-time control of the underlying device continues to run on the device's existing stack. See `docs/limits/real-time-boundary.md`.
- A safety system replacement. The adapter does not override the device's safety controller. See `docs/limits/safety-system-boundary.md`.
- A guaranteed lossless bridge. Some semantics in the native protocol have no WCP equivalent (and vice versa); the adapter documents what it preserves and what it drops.

## Adapters in this directory

| Adapter | South-bound protocol | Domain | Status |
|---|---|---|---|
| `mavlink-drone/` | MAVLink 2.0 (PX4, ArduPilot) | aerial inspection, mapping | preview |
| `vda5050-warehouse-amr/` | VDA 5050 v2.0.0 (MQTT-framed JSON) | warehouse logistics | preview, implements RFC 0024 |
| `modbus-plc-gateway/` | Modbus TCP | industrial automation, smart cities | preview |
| `mqtt-iot/` | MQTT v5.0 | IoT sensor fleets, agriculture, environmental monitoring | preview |
| `ros1-compat/` | ROS 1 Noetic (via `ros1_bridge`) | research and legacy industrial robots | preview |
| `vendor-robot-bridge-template/` | (template, vendor-specific) | generic robot bridge starter | template |

`preview` adapters ship working WCP-side bridge code plus a documented setup procedure for the native protocol. Native-protocol verification on this build host is limited to import-and-syntax checks plus unit tests for the WCP-side bridge logic; full end-to-end runs require the corresponding native runtime (PX4 SITL, a VDA 5050 simulator, a Modbus simulator, a Mosquitto broker, ROS 1 Noetic, etc.).

## Selection guide: which adapter do I want?

```
Is the device's native protocol one of the above?
|
+-- Yes: copy the matching adapter and customize.
|
+-- No, but it's serial/RS-485 with a register map:
|     -> modbus-plc-gateway (most industrial PLCs and many SCADA boxes
|        support Modbus TCP via a serial-to-IP gateway).
|
+-- No, but it publishes telemetry to a broker:
|     -> mqtt-iot (covers a huge fraction of consumer IoT and field
|        sensor deployments).
|
+-- No, but it's a research robot with a ROS 1 or ROS 2 stack:
|     -> ros1-compat (ROS 1 via ros1_bridge);
|        for ROS 2 native, use wcp_worker (see examples/agents/).
|
+-- No, it's a proprietary protocol with a vendor SDK:
      -> vendor-robot-bridge-template (skeleton you fill in
         with the vendor's API client).
```

## Common structure

Every adapter follows the same file layout:

- `bridge.py` (or `gateway.py`): the long-running WCP worker that holds the south-bound connection and translates messages.
- `capability.py`: builds the `CapabilityDescriptor` that the adapter declares to the coordinator. This is where the device's native capabilities (payload, range, sensors, end-effectors, etc.) become a WCP capability declaration.
- `README.md`: setup steps, what the adapter does and does not preserve, how to test.

Adapters that need extra files (e.g., a simulator config, a docker-compose for the native runtime) include them in the adapter's own directory.

## Capability declaration conventions

All adapters declare:

- `worker_class`: one of the registered classes (typically `autonomous_robot`, `teleoperated_system`, or `hybrid_human_robot`)
- `class_extension`: device-specific capability fields (kinematics, payload, sensors, etc.)
- `attestation_keys`: the adapter's signing key (the device usually does not sign WCP evidence directly; the adapter signs on its behalf, with the device's authentication backing the adapter's `signer_identifier`)
- `connectivity_profile`: typically `continuous` for adapters running on stable infrastructure, but `intermittent` for adapters running on the device itself (e.g., on-drone)

## How evidence flows through an adapter

```
device's native telemetry (MAVLink HEARTBEAT,
   VDA 5050 State message, Modbus register read,
   MQTT message, ROS 1 topic)
        |
        v
  adapter's translator
        |
        v
  WCP attestation evidence payload
   (signed by the adapter's attestation key,
    in the appropriate evidence kind per RFC 0003)
        |
        v
  coordinator's verifier
        |
        v
  audit chain entry
```

The adapter does NOT relay raw native-protocol bytes upstream. The adapter is responsible for producing a WCP evidence payload that conforms to a registered evidence kind (e.g., `indoor_pose_track`, `iot_beacon_proximity`, `geo_track`, custom kinds the operator has registered).

## Trust and signing

The adapter's `attestation_keys[*].trust_class` (RFC 0033 preview) reflects the adapter's signing posture, not the underlying device's. If the device has TPM2 or an HSM, the adapter MAY declare `hardware-attested-tpm2`; if the adapter signs in software on a generic host, declare `software-keypair`. Misdeclaration is a protocol violation.

## See also

- `docs/limits/wcp-is-not.md` for the full non-use list
- `docs/limits/real-time-boundary.md` for the orchestration vs control split
- `docs/limits/safety-system-boundary.md` for safety controller boundary
- `rfcs/0024-vda5050-adapter.md` for the VDA 5050 design rationale
- `rfcs/0003-evidence-kinds-registry.md` for evidence kind registration
- `rfcs/0033-attestation-key-trust-classes.md` for trust class semantics
