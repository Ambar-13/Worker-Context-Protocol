# Reference Agent: industrial-maintenance

**Domain:** heavy industry (one of many WCP domains; for further reading see `logistics/`, `infrastructure/` templates).

**Scenario:** An AI agent schedules cooling-tower-bearing inspections at a heavy-industry site. A hybrid worker class is eligible: human inspectors or autonomous wall-climbing robots with thermal imaging. Attestation requires thermal-imagery sensor evidence plus a building-supervisor sign-off.

**Worker class:** `hybrid` (can be claimed by `human` or `autonomous_robot`). Same 9 RPCs handle both.

**Descriptor type:** `observe_and_report`.

**Attestation modes:** `sensor-witness` (signed thermal-camera recording) + `third-party-witness` (supervisor signature).

## Run

`./run.sh`

## What this proves

The agent does not branch on worker class. The thermal recording is `sensor-witness` whether collected by a human's tripod-mounted camera or a robot's onboard array; the verifier discriminates by `kind` (`signed_sensor_recording`), not by class. This is the central D4 invariant in code.
