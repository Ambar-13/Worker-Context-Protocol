# Reference Agent: logistics

**Domain:** warehouse and supply-chain operations (one of many WCP domains; for further reading see `industrial-maintenance/`, `manufacturing/` templates).

**Scenario:** An AI agent dispatches pallet moves from receiving to staging. Either an autonomous mobile robot (AMR) or a human forklift operator can claim, whichever satisfies time and certification constraints. Attestation: indoor-pose track + weight-delta confirmation.

**Worker class filter:** `autonomous_robot` OR `human`. The single most direct illustration of WCP's worker-class agnosticism.

**Descriptor type:** `transport`.

**Attestation modes:** `sensor-witness` (`indoor_pose_track` + `weight_delta`) + `third-party-witness` (`iot_beacon_proximity` at the staging bay).

## Run

`./run.sh`
