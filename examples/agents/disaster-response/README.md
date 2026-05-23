# Reference Agent: disaster-response

**Domain:** emergency services (one of many WCP domains; further reading: `infrastructure/`, `healthcare/`).

**Scenario:** An AI agent routes mixed teleoperated_robot, autonomous_robot, and human teams to damage zones after an incident. The agent posts `observe_and_report` tasks for each zone; multi-source imagery (drone RGB, ground-vehicle RGB, human-held smartphone) cross-attests the same scene. The verifier accepts the same `(mode, kind)` evidence regardless of which worker class collected it.

**Worker class filter:** `autonomous_robot`, `teleoperated_robot`, `human` (any of the three can contribute attestations).

**Descriptor type:** `observe_and_report`.

**Attestation modes:** `sensor-witness` (multiple `photo_with_exif` and `signed_sensor_recording`) cross-attested across at least three independent worker DIDs.

## Run

`./run.sh`
