# {{NAME}}

WCP worker scaffold for **industrial robotics fleets**.

Class: `{{CLASS}}`. Domain template: `industrial`.

## What WCP does for this domain

The Worker Context Protocol coordinates AI agents and physical-world workers
across a broad set of institutional domains. This template is for **industrial robotics fleets**.
Typical use cases include: AMR fleet dispatch in a factory, automated palletizing, robotic press tending.

Adjacent domains served by the same protocol include manufacturing, construction. See the full
list of 14 domain templates via `wcp init worker --help`.

## Descriptor types implemented

- `transport`
- `scheduled_presence`
- `observe_and_report`

## Run

```bash
pip install -r requirements.txt
wcp dev
```

## Next steps

- Open `worker.py` and replace handler bodies with real work.
- Run `wcp register --coordinator <wss-url>` to publish capabilities remotely.
- Run `wcp test --conformance --level 1` to verify the coordinator you target.
