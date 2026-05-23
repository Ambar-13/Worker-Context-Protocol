# MAVLink-to-WCP Adapter

A bridge that exposes a MAVLink 2.0 vehicle (PX4, ArduPilot, or any autopilot speaking the common MAVLink dialect) as a WCP worker.

## What it does

- Connects to a vehicle's MAVLink endpoint (UDP, serial, or TCP)
- Reads `AUTOPILOT_VERSION`, `HEARTBEAT`, and vehicle parameters to populate a WCP `CapabilityDescriptor`
- Accepts WCP tasks of type `aerial_inspection`, `aerial_survey`, and `aerial_delivery_lite`
- Translates the task's `descriptor_payload` (waypoints, takeoff alt, landing point) into MAVLink mission items (`MISSION_ITEM_INT`)
- Uploads the mission, arms, starts AUTO mode
- Streams `GLOBAL_POSITION_INT` into a `geo_track` evidence buffer
- On mission complete, signs and submits the `geo_track` attestation evidence

## What it does NOT do

- Override the vehicle's failsafes, geofence, RTL behavior, or operator's RC commands. Safety/RC control authority remains with the autopilot. See `docs/limits/safety-system-boundary.md`.
- Perform real-time guidance loops. The 50-400 Hz attitude/position control loops continue to run on the autopilot. WCP operates at the mission-dispatch granularity. See `docs/limits/real-time-boundary.md`.
- Validate that the requested mission is safe or legal in the local airspace. Airspace authorization, NOTAM filing, BVLOS waivers, etc. are operator-side.

## Files

- `bridge.py`: the WCP worker process and the MAVLink-to-WCP translation layer
- `capability.py`: `CapabilityDescriptor` builder for an aerial vehicle
- `__init__.py`: package marker

## Dependencies

Production deployments require one of:

- `pymavlink` (lightweight, sync-style API; wrap in an executor for the async surface)
- `mavsdk` (modern Python bindings, gRPC-backed; pairs naturally with PX4)
- a custom MAVLink client (acceptable; conform to the `MAVLinkConnection` Protocol in `bridge.py`)

The reference code does not import any of these by default so the WCP-side bridge logic stays testable on a CI runner without a flight-stack install.

## Local testing

### Option A: PX4 SITL

```
# Terminal 1: PX4 software-in-the-loop
make px4_sitl jmavsim   # or gazebo

# Terminal 2: WCP coordinator (this repo)
python -m wcp_coordinator

# Terminal 3: this bridge
export WCP_COORDINATOR=ws://localhost:8000/wcp/ws
export MAVLINK_ENDPOINT=udp://:14540
python -m examples.adapters.mavlink_drone.bridge
```

### Option B: ArduPilot SITL

Equivalent: launch `sim_vehicle.py` from the ArduPilot tree with `--out udp:127.0.0.1:14540`, then run the bridge with `MAVLINK_ENDPOINT=udp://:14540`.

### Option C: unit-only

Unit-test the WCP-side translation (`descriptor_to_mavlink_mission`, `_GeoTrackBuffer.to_evidence_payload`) without any MAVLink runtime. See the inline `MAVLinkConnection` Protocol; a fake implementation suffices.

## Evidence kinds produced

| Kind | Source | Notes |
|---|---|---|
| `geo_track` | `GLOBAL_POSITION_INT` stream | sampled at the vehicle's rate (typically 5-10 Hz); the adapter MAY downsample before submission |
| `barometric_altitude_profile` | `VFR_HUD.alt` or `SCALED_PRESSURE` | optional; produced when the task descriptor requests altitude-of-record |
| `image_capture_manifest` | DO_DIGICAM_CONTROL + camera component messages | the adapter records capture metadata, not image bytes; bytes flow out-of-band per operator policy |
| `thermal_capture_manifest` | thermal-payload component messages | same as RGB, on the thermal channel |

## Trust class

The adapter declares `trust_class = "software-keypair"` by default. If the bridge host has a TPM2 or HSM-backed key, the operator MAY change this to `hardware-attested-tpm2` (RFC 0033 preview). Note that the trust class describes the adapter's signing posture, not the autopilot's.

## Connectivity profile

The adapter declares `connectivity_profile = "intermittent"` because aerial workers frequently lose ground-station link. WCP-Lite buffer-and-replay applies; see `wcp_sdk_python/wcp_sdk/preview/wcp_lite.py`.

## What WCP semantics this adapter does NOT preserve

- MAVLink severity levels on `STATUSTEXT` messages are not surfaced as WCP audit-chain severity. Operators wanting MAVLink STATUSTEXT in the audit chain should configure a side-channel logger.
- MAVLink command acknowledgement timing is collapsed into the WCP `tasks/attest` cycle; per-command MAV_CMD_ACK_OK timestamps are not exposed.
- MAVLink RC override semantics have no WCP equivalent; the adapter does NOT translate WCP supervision handoffs into RC override commands.

## See also

- `rfcs/0003-evidence-kinds-registry.md` for evidence kind registration
- `rfcs/0029-wcp-lite.md` for the intermittent-connectivity model
- `rfcs/0033-attestation-key-trust-classes.md` for trust class declaration
