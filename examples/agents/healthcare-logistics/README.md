# Reference Agent: healthcare-logistics

**Domain:** regulated healthcare operations (further reading: `scientific/`, `emergency/`).

**Scenario:** An AI agent dispatches medical-specimen transport between a draw site and a reference lab. The specimen must remain in a temperature-controlled container; the transport must be witnessed by chain-of-custody signatures at pickup and dropoff. Worker class can be human courier or temperature-controlled AMR.

**Worker class filter:** `human` OR `hybrid` (a courier with a regulated cold-chain box).

**Descriptor type:** `transport`.

**Attestation modes:** `sensor-witness` (`signed_sensor_recording` for the cold-chain temperature log) + `owner-sign-off` (chain-of-custody signatures at both endpoints).

## Run

`./run.sh`
