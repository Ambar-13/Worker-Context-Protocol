# Reference Agent: scientific-ops

**Domain:** research operations (one of many WCP domains; for further reading see `industrial-maintenance/`, `healthcare-logistics/`).

**Scenario:** An AI agent schedules instrument calibration runs across a wet-lab facility. Calibration must be witnessed by a technician on-site, recorded by the instrument's own log signature, and completed within a calibration window. The agent posts the task; a human technician worker claims; on-site presence is verified by geofence check-in/out plus the instrument's signed log file.

**Worker class:** `human` (the technician). The same scenario could mount on `semi_autonomous` (a teleoperated calibration assistant) without changes to the protocol surface.

**Descriptor type:** `scheduled_presence`.

**Attestation modes:** `cryptographic-presence` (technician phone geofence) + `sensor-witness` (signed instrument log hash).

## Run

```bash
. ../../../.venv/bin/activate
python -m uvicorn wcp_dev_runtime.coordinator_dev_app:app --port 8000 &
sleep 2
python worker.py &
python agent.py
```

Or simply `./run.sh`.

## What this proves

The same eight RPCs handle this research-operations dispatch with no modification. The variance vs the other five reference agents lives entirely in `descriptor_payload` and the `(mode, kind)` pairs in the attestation requirement.
