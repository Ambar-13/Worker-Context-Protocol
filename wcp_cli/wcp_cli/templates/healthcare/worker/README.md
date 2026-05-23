# {{NAME}}

WCP worker scaffold for **regulated healthcare operations**.

Class: `{{CLASS}}`. Domain template: `healthcare`.

## What WCP does for this domain

The Worker Context Protocol coordinates AI agents and physical-world workers
across a broad set of institutional domains. This template is for **regulated healthcare operations**.
Typical use cases include: specimen transport with cold-chain attestation, supply rounds, equipment relocation.

Adjacent domains served by the same protocol include scientific, emergency. See the full
list of 14 domain templates via `wcp init worker --help`.

## Descriptor types implemented

- `transport`
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
