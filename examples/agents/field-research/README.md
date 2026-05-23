# Reference Agent: field-research

**Domain:** scientific field operations (further reading: `scientific/`, `agriculture/`, `maritime/` templates).

**Scenario:** An AI agent dispatches environmental-sample collection runs to field researchers. Each collection requires GPS-stamped arrival, time-stamped sample chain-of-custody, and a signed sensor recording from the field instrument. Multiple sites; one worker visits a route.

**Worker class:** `human` (the researcher). Could be `autonomous_robot` (sample drone) without protocol change.

**Descriptor type:** `observe_and_report`.

**Attestation modes:** `sensor-witness` (`gps_track` + `signed_sensor_recording`).

## Run

`./run.sh`
