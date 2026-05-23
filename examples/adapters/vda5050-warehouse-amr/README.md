# VDA 5050 Warehouse-AMR-to-WCP Adapter

Reference adapter that bridges a VDA 5050 v2.0.0 fleet to WCP. Implements RFC 0024.

## What VDA 5050 is

VDA 5050 is the German automotive industry's interface specification for communication between AGV/AMR control systems and master controllers. It is published by the VDA (Verband der Automobilindustrie) and is the dominant interoperability standard in the warehousing-AMR space, with a substantial installed base across automotive, e-commerce fulfillment, and 3PL deployments.

The protocol uses MQTT with a fixed topic structure and JSON message schemas:

```
uagv/v2/<manufacturer>/<serialNumber>/{order,instantActions,state,visualization,factsheet,connection}
```

## What this adapter does

- Subscribes to a VDA 5050 fleet's broker
- Reads the AMR's `factsheet` to derive a WCP `CapabilityDescriptor`
- Accepts WCP `transport` and `pickup_dropoff` tasks
- Translates the WCP descriptor's pickup/dropoff into a VDA 5050 `order` (nodes + edges + pick/drop actions)
- Publishes the order to the AMR's order topic
- Watches the `state` topic for progress and order completion
- Submits an `indoor_pose_track` attestation evidence payload assembled from the state samples

## What it does NOT do

- Replace the fleet master controller. If the deployment already has a VDA 5050 master controller (e.g., a fleet manager from a vendor), this bridge operates as a peer order producer; in single-master deployments, the existing master must be reconfigured to coexist or the bridge replaces it.
- Plan paths. The AMR's local autonomy plans between the named nodes. The bridge produces minimum two-node orders (pickup, dropoff); more complex routes require external path planning before order construction.
- Translate VDA 5050 `instantActions` for emergency stop. The safety stop is the deployment's responsibility (E-stop button on the AMR, safety scanners, etc.). See `docs/limits/safety-system-boundary.md`.

## Files

- `bridge.py`: WCP worker that mediates between the coordinator and the AMR's MQTT topics
- `capability.py`: translates a VDA 5050 Factsheet into a WCP `class_extension`
- `__init__.py`: package marker

## Dependencies

- `asyncio-mqtt` or `paho-mqtt` (the bridge conforms to a small `MQTTClient` Protocol; either backs it)
- A VDA 5050 simulator or a live fleet for end-to-end testing (e.g., `vda5050-simulator` projects on GitHub, or a fleet vendor's own test rig)

## Local testing

### Option A: against a VDA 5050 simulator

```
# Terminal 1: Mosquitto broker
mosquitto -p 1883

# Terminal 2: a VDA 5050 simulator publishing as <manufacturer>/<serial>
# (e.g., openTCS-AGV-simulator or equivalent)

# Terminal 3: WCP coordinator
python -m wcp_coordinator

# Terminal 4: this bridge
export WCP_COORDINATOR=ws://localhost:8000/wcp/ws
export VDA5050_BROKER=mqtt://localhost:1883
python -m examples.adapters.vda5050_warehouse_amr.bridge
```

### Option B: unit-only

The translation functions (`wcp_transport_to_vda5050_order`, `vda5050_state_to_attestation_payload`, `factsheet_to_class_extension`) are pure functions and unit-testable without an MQTT runtime.

## Evidence kinds produced

| Kind | Source | Notes |
|---|---|---|
| `indoor_pose_track` | accumulated `agvPosition` from `state` messages | sampled at the fleet's state-publish rate |
| `weight_delta` | optional; `loads[]` changes in state | use when the AMR reports load mass |
| `iot_beacon_proximity` | optional; if the warehouse has UWB/BLE beacons | not produced by VDA 5050 directly; would require a side input |
| `vda5050_order_log` | the raw sequence of order + state messages for the order | operator-defined evidence kind for full forensic record |

The last kind (`vda5050_order_log`) is operator-defined and not in the v1.0-rc1 default registry. Operators wishing to use it MUST register it in their coordinator per RFC 0003.

## What VDA 5050 semantics this adapter does NOT preserve

- `instantActions` (emergency stop, cancel, pause) are not bridged into WCP. WCP's supervision handoff and `tasks/abort` flow do not have one-to-one VDA 5050 counterparts; the operator's runbook handles this.
- `visualization` messages (high-rate pose for HMI display) are ignored. The bridge consumes `state` messages, which are the source of authoritative order progress.
- VDA 5050 error severity (FATAL, WARNING) is collapsed; only FATAL triggers a `tasks/supervise` transition in this preview.

## See also

- `rfcs/0024-vda5050-adapter.md` for the original RFC
- `rfcs/0003-evidence-kinds-registry.md` for evidence kind registration
- `examples/agents/logistics/` for an end-to-end logistics worked example WCP-native
