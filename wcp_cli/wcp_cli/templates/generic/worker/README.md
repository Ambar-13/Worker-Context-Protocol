# {{NAME}}

WCP worker scaffold. Class: `{{CLASS}}`. Domain template: `{{DOMAIN}}` (generic).

## Run

```bash
pip install -r requirements.txt
wcp dev
```

## What this worker does

Implements two descriptor types from `spec/1.0-rc1.md`:

- `scheduled_presence`: be present in a zone for a duration.
- `observe_and_report`: collect sensor evidence across a polygon.

The cryptographic-presence attestation mode is wired up; extend `attest_presence`
or add additional `@worker.attest(...)` handlers for sensor-witness, third-party-
witness, or owner-sign-off as your application requires.

## Next steps

- Open `worker.py` and replace the `handle_*` bodies with real work.
- Edit `wcp.yaml` to point at your coordinator.
- Run `wcp register --coordinator <wss-url>` to publish capabilities to a remote coordinator.
- Run `wcp test --conformance --level 1` to verify the coordinator you target.
