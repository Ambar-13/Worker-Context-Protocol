# Reference Agents

Six reference agents demonstrate WCP's D4 forcing function across institutionally distinct domains. Each runs against a local coordinator started by `wcp dev`, exercises the same nine RPCs, and completes a full task lifecycle (post -> claim -> execute -> attest -> settle).

| Agent | Domain | Worker class focus | Attestation modes |
|---|---|---|---|
| `scientific-ops/` | research operations | human technician | sensor-witness + cryptographic-presence |
| `industrial-maintenance/` | heavy industry | hybrid (human + autonomous_robot) | sensor-witness (thermal imagery) + third-party-witness |
| `disaster-response/` | emergency services | mixed teleoperated_robot + autonomous_robot + human | sensor-witness (multi-source imagery) cross-attested |
| `logistics/` | warehouse and supply-chain operations | autonomous_robot OR human forklift operator | sensor-witness (indoor pose) + third-party-witness |
| `field-research/` | scientific field operations | human researcher | sensor-witness (GPS + timestamp + signed sensor) |
| `healthcare-logistics/` | regulated healthcare operations | hybrid courier | sensor-witness (cold-chain temperature) + owner-sign-off (chain-of-custody) |

These are six visibly different institutional domains. The same nine RPCs handle every one. This is the proof in code of `spec/d4-verification-1.0-rc1.md`.

## Run any agent

```bash
# 1. start a local coordinator
. .venv/bin/activate
python -m uvicorn wcp_dev_runtime.coordinator_dev_app:app --port 8000 &

# 2. run the agent + worker pair for a given domain
cd examples/agents/<agent-name>
python worker.py &
python agent.py
```

Each agent's `run.sh` automates step 2.

## What "institutionally distinct" means

The six domains span: regulated research, heavy industry, emergency response, supply-chain operations, scientific field operations, and regulated healthcare. None of them is a consumer service. WCP's coordination primitives are the same across all six; the domain shows up only in the application-layer `descriptor_payload` and the registered `(mode, kind)` pairs the verifier accepts.

For a broader view of which domains WCP serves, see `wcp_cli/wcp_cli/templates/` (14 starter templates) and `spec/d4-verification-1.0-rc1.md` (the forcing-function proof).
