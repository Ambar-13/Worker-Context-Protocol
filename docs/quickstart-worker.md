# Quickstart: Build and Run a WCP Worker in Five Minutes

This quickstart shows the v1.0-rc2 decorator-style Python SDK. Primary illustration: **industrial-maintenance** (a hybrid worker that does cooling-tower thermal inspections). The same flow applies across the 14 domain templates.

## Prerequisites

- Python 3.11+
- `pip install wcp wcp-sdk`

## 1. Scaffold

```bash
wcp init worker thermal-inspector --class hybrid --domain industrial
cd thermal-inspector
```

You get:

```
thermal-inspector/
  worker.py
  wcp.yaml
  requirements.txt
  README.md
```

## 2. Start a local coordinator + worker

In one terminal:

```bash
pip install -r requirements.txt
wcp dev
```

This launches a local coordinator on `localhost:8000` and runs `worker.py`. The worker publishes its CapabilityDescriptor on connect.

## 3. Customize handlers

Open `worker.py`:

```python
from wcp_sdk.v2 import Worker
from wcp_sdk.types import AttestationMode

worker = Worker(
    name="thermal-inspector",
    worker_class="hybrid",
    coordinator="ws://localhost:8000/wcp/ws",
)

@worker.capability(descriptor_types=["observe_and_report"])
def declare(): ...

@worker.handle("observe_and_report")
async def inspect(task: dict) -> dict:
    asset = task["descriptor_payload"]["asset_id"]
    # Your inspection logic here.
    return {"inspected_at": "...", "asset_id": asset}

@worker.attest(AttestationMode.SENSOR_WITNESS)
async def attest_thermal(claim_id, task):
    return {
        "kind": "signed_sensor_recording",
        "payload": {"recording_hash": "...", "duration_seconds": 120},
    }

if __name__ == "__main__":
    worker.run()
```

## 4. Register with a remote coordinator

For non-dev use:

```bash
wcp register --coordinator wss://your-coordinator.example.org/wcp/ws
```

`wcp.yaml` carries the persistent key path and config.

## 5. Verify with the conformance suite

```bash
wcp test --conformance --level 1 --target wss://your-coordinator.example.org/wcp/ws
```

## Domain alternatives

The same flow works for the 13 other domains. Run `wcp init worker --help` for the full list (industrial, scientific, emergency, logistics, agriculture, healthcare, infrastructure, disaster, research, manufacturing, smart-city, maritime, construction, generic). Each template ships handlers and attestation modes appropriate to that domain.

## Next steps

- See `docs/quickstart-agent.md` for the agent side.
- See `docs/quickstart-coordinator.md` to deploy a coordinator.
- See `docs/llm-integration.md` to drive task posting from a Claude / GPT / Gemini agent.
- See the six reference agents at `examples/agents/` for end-to-end demonstrations across institutionally distinct domains.
