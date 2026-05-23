# {{NAME}}

WCP worker scaffold for **warehouse and supply-chain operations**.

Class: `{{CLASS}}`. Domain template: `logistics`.

## What WCP does for this domain

The Worker Context Protocol coordinates AI agents and physical-world workers
across a broad set of institutional domains. This template is for **warehouse and supply-chain operations**.
Typical use cases include: pallet moves, dock-to-stock transfers, cross-dock relays.

Adjacent domains served by the same protocol include manufacturing, industrial. See the full
list of 14 domain templates via `wcp init worker --help`.

## Descriptor types implemented

- `transport`

## Run

```bash
pip install -r requirements.txt
wcp dev
```

## Next steps

- Open `worker.py` and replace handler bodies with real work.
- Run `wcp register --coordinator <wss-url>` to publish capabilities remotely.
- Run `wcp test --conformance --level 1` to verify the coordinator you target.
