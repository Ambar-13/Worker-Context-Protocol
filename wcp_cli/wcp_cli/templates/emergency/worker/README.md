# {{NAME}}

WCP worker scaffold for **emergency response dispatch**.

Class: `{{CLASS}}`. Domain template: `emergency`.

## What WCP does for this domain

The Worker Context Protocol coordinates AI agents and physical-world workers
across a broad set of institutional domains. This template is for **emergency response dispatch**.
Typical use cases include: first-responder routing, drone scouts, supply drops to incident sites.

Adjacent domains served by the same protocol include disaster, healthcare. See the full
list of 14 domain templates via `wcp init worker --help`.

## Descriptor types implemented

- `transport`
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
