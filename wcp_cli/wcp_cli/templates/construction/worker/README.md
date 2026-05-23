# {{NAME}}

WCP worker scaffold for **construction inspection**.

Class: `{{CLASS}}`. Domain template: `construction`.

## What WCP does for this domain

The Worker Context Protocol coordinates AI agents and physical-world workers
across a broad set of institutional domains. This template is for **construction inspection**.
Typical use cases include: site-progress drone surveys, daily safety walks, equipment-location audits.

Adjacent domains served by the same protocol include infrastructure, manufacturing. See the full
list of 14 domain templates via `wcp init worker --help`.

## Descriptor types implemented

- `observe_and_report`
- `scheduled_presence`

## Run

```bash
pip install -r requirements.txt
wcp dev
```

## Next steps

- Open `worker.py` and replace handler bodies with real work.
- Run `wcp register --coordinator <wss-url>` to publish capabilities remotely.
- Run `wcp test --conformance --level 1` to verify the coordinator you target.
