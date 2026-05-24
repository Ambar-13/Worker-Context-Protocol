# Worker Context Protocol (WCP)

**Version:** v0.955  ·  **License:** Apache 2.0  ·  **Schema:** `wcp/0.2`

## What WCP is

WCP is an open wire protocol for AI agents to dispatch physical-world work. One RPC surface lets an agent post the same task to a human technician, an autonomous robot, a teleoperated platform, or a hybrid worker; the matching engine and the attestation verifier read what the worker can do and what evidence it emits, never what class the worker belongs to.

The lever is the same one the Model Context Protocol (MCP) carries for software tools — in-band capability discovery plus a typed call contract. Physical work needs three primitives MCP does not: a typed attestation mechanism with an M-of-N evaluator, an attestation retry loop for evidence the verifier rejects, and a hash-linked audit chain that spans federated coordinators. Settlement, escrow, and dispute resolution sit above WCP; they subscribe to the audit chain and run their own value-flow logic.

The repository ships a Python reference coordinator, four client SDKs, seven worked agents across institutionally distinct domains, a two-coordinator federation demo, a partial-graph three-coordinator variant, and a three-level conformance suite that passes 33 of 33 cases. Everything is open-source under Apache 2.0.

---

## Five-minute hello world

```bash
# Install the CLI and SDK
pip install wcp wcp-sdk

# Scaffold a worker (hybrid worker for cooling-tower thermal inspections)
wcp init worker thermal-inspector --class hybrid --domain industrial
cd thermal-inspector
pip install -r requirements.txt

# Start a local coordinator alongside the worker
wcp dev
```

In a second terminal:

```bash
cd ../examples/agents/industrial-maintenance
python agent.py
```

You will see `tasks/post` round-trip through the coordinator, the worker auto-claim and attest, and a `task_completed` entry land on the audit chain on disk. Roughly five minutes from `pip install` to a signed audit-chain entry.

To explore a different domain, swap the `--domain` flag. Fourteen templates ship under `wcp_cli/wcp_cli/templates/`, each with handlers and attestation modes appropriate to the domain.

---

## The wire surface

WCP is ten remote-procedure calls. Eight carry the task lifecycle:

| Call | Direction | Role |
|---|---|---|
| `capabilities/list` | client → coordinator | discover what workers can do |
| `capabilities/subscribe` | client → coordinator | stream capability changes |
| `tasks/post` | agent → coordinator | post a task |
| `tasks/claim` | worker → coordinator | claim a task with a signed acceptance |
| `tasks/execute` | worker ↔ coordinator | execute and heartbeat |
| `tasks/attest` | worker → coordinator | submit evidence |
| `tasks/supervise` | supervisor ↔ coordinator | hand the session over or take it back |
| `tasks/abort` | either → coordinator | bail out cleanly |

The remaining two are administrative — outside the task hot path:

| Call | Direction | Role |
|---|---|---|
| `capabilities/upsert` | worker → coordinator | self-register a capability descriptor |
| `audit/observe` | inspector → coordinator | read a chain segment by `claim_id` or `task_id` |

The full normative specification is in `spec/0.2.md`; the v0.955 changes are in `spec/0.955.md`.

---

## What changed in v0.955

v0.955 removes settlement, escrow, dispute, and refund primitives from the wire protocol. The marketplace-flavoured `disputed` and `refunded` terminal states are gone; in their place, a recheck mechanism — when the verifier rejects evidence, the worker re-attests up to `max_attestation_attempts` times before the task voids. Marketplaces, ERPs, grant systems, and any other settlement layer subscribe to the audit chain (`task_completed`, `task_voided`, `task_aborted`) and run their value-flow logic outside the protocol. WCP is now strictly a coordination protocol. Migration guide and full change list in `spec/0.955.md`.

---

## Seven reference agents across institutionally distinct domains

The same ten RPCs handle every domain below. The variance lives in `descriptor_payload` and the registered `(mode, kind)` evidence pairs the verifier accepts; the wire surface does not change.

| Domain | Path | What the agent does |
|---|---|---|
| Research operations | `examples/agents/scientific-ops/` | Instrument calibration; technician on-site plus signed instrument log |
| Heavy industry | `examples/agents/industrial-maintenance/` | Cooling-tower-bearing thermal inspections; hybrid human + robot workers |
| Emergency services | `examples/agents/disaster-response/` | Mixed drone + ground + human teams to damage zones; 3-of-5 cross-attested imagery |
| Warehouse / supply chain | `examples/agents/logistics/` | Pallet moves; AMR or human forklift operator, whichever claims first |
| Field science | `examples/agents/field-research/` | Environmental sample-collection routes; GPS plus signed sensor manifest |
| Regulated healthcare | `examples/agents/healthcare-logistics/` | Medical specimen transport; cold-chain temperature log plus chain-of-custody signatures |
| Robot-to-robot | `examples/agents/delivery-robot-dispatcher/` | An autonomous mobile robot hands a `transport` task to a stationary manipulator for the place step |

Each agent runs end-to-end against a local coordinator via `./run.sh` or directly via `python agent.py`.

Templates for seven additional domains (agriculture, infrastructure, manufacturing, smart-city, maritime, construction, generic) ship under `wcp_cli/wcp_cli/templates/`.

---

## The specification

`spec/0.2.md` is the full normative document (~30 pages). Companion normative documents in `spec/`:

- `threat-model.md` — STRIDE per RPC and per trust boundary
- `privacy-architecture.md` — PII tagging, hash-only audit chain, tombstone pattern, PDPA / GDPR / CCPA alignment
- `federation.md` — cross-coordinator capability discovery and audit-chain interop
- `conformance.md` — the three levels and what each one tests
- `did-method-wcp.md` — W3C DID Core registration for `did:wcp`
- `d4-verification-0.2.md` — six base D4 cells plus four federation cells, all passing
- `semver-policy.md`, `error-codes.md`, `security-baseline.md`, `time-synchronization.md`, `retry-idempotency.md`, `performance-conformance.md`

## Languages

| Language | Path | Package | Status |
|---|---|---|---|
| Python | `wcp_sdk_python/` | `wcp-sdk` (PyPI) | reference SDK; v1 + v2 decorator API; 23 tests passing |
| TypeScript | `wcp_sdk_typescript/` | `@wcp/sdk` (npm) | worker + agent core; Node 20+, browser-ready |
| Rust | `wcp_sdk_rust/` | `wcp-sdk` (crates.io) | Tokio async; builder pattern; for embedded workers |
| Go | `wcp_sdk_go/` | `github.com/wcp-spec/wcp-go` | idiomatic Go: interfaces, contexts |

## LLM framework integrations

`integrations/` ships adapters for Anthropic, OpenAI, Gemini, LangChain, AutoGen, LlamaIndex, CrewAI, and the Vercel AI SDK. Each exposes the same four tools (`wcp_discover_capabilities`, `wcp_post_task`, `wcp_subscribe_attestation`, `wcp_get_audit_chain`). Worked examples across multiple domains are in `docs/llm-integration.md`.

## CLI

```bash
wcp init worker <name> --class <C> --domain <D>   # 14 domain templates
wcp init agent <name> --llm <L>                   # 4 LLM provider templates
wcp init coordinator <name>                       # Docker Compose deployment
wcp dev                                           # local coordinator + worker
wcp test --conformance [--level N]                # run the conformance suite
wcp inspect                                       # visual inspector at :8765
wcp register --coordinator <wss-url>              # publish to a remote coordinator
wcp doctor                                        # environment diagnostic
```

## Visual inspector

```bash
wcp inspect
```

Single-page UI at `http://localhost:8765` that connects to your coordinator's WebSocket and shows health, active tasks, audit-chain tail, and RPC traffic. Read-only by default.

## Deployment

| Target | Path |
|---|---|
| Docker Compose | `deployments/docker-compose.yml` |
| Kubernetes (Helm) | `deployments/helm/wcp-coordinator/` |
| Render | `deployments/render.yaml` |
| Railway | `deployments/railway.toml` |
| Fly.io | `deployments/fly.toml` |

Work through `deployments/PRODUCTION_HARDENING.md` before exposing public traffic.

## What WCP does not solve

The protocol earns trust by being explicit about where its scope ends. Sub-millisecond real-time control runs inside the worker on EtherCAT, TSN, DDS, or ROS 2 with a real-time kernel; WCP carries the assignment and the attestation, not the control loop. Functional-safety certification (IEC 61508, ISO 13849, ISO 13482, etc.) lives in the certified hardware and the operator's risk assessment; WCP records evidence, it does not enforce. Swarm coordination runs on dedicated runtimes and presents to WCP as a single worker. Attestation independence — whether the parties supplying evidence are actually independent — lives in the deployment's vetting layer; WCP provides the typed primitive over which collusion-resistance policies can be expressed, but it does not certify those policies. `docs/limits/` enumerates the full set with workaround patterns and failure conditions.

## Governance

- License: Apache 2.0
- `DONATION_COMMITMENT.md` — written commitment to donate stewardship to a neutral foundation by v1.0 final
- `NON_COERCION_COMMITMENT.md` — 5x integration-time ratio between WCP and non-WCP integrations
- `TRADEMARK_POLICY.md` — pre-v1.0 non-enforcement commitment
- `CHARTER.md`, `RFC_PROCESS.md`, `TSC_BYLAWS.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`

## Layout

```
spec/                       # normative specification (v0.2)
wcp_cli/                    # `wcp` CLI plus 14 domain templates
wcp_sdk_python/             # Python SDK (v1 + v2 decorator API)
wcp_sdk_typescript/         # @wcp/sdk (TypeScript)
wcp_sdk_rust/               # wcp-sdk (Rust crate)
wcp_sdk_go/                 # wcp-go (Go module)
wcp_coordinator/            # FastAPI reference backend (frozen v0.2)
wcp_worker/                 # ROS 2 Humble reference plugin (frozen v0.2)
pwa/wcp/                    # PWA module (frozen v0.2)
wcp_dev_runtime/            # `wcp dev` ASGI app wrapper
examples/agents/            # seven reference agents across distinct domains
integrations/               # eight LLM-framework adapters
inspector/                  # `wcp inspect` web UI
deployments/                # Docker Compose, Helm, Render, Railway, Fly
conformance/                # conformance suite (Python runner + Level 1-3 bundles)
operator-guide/             # recommended deployment practice; not normative
rfcs/                       # technical RFCs and open v1.1 questions
docs/                       # quickstarts, migration, LLM integration
```

## Pre-v1.0 final

This is a release candidate. v1.0 final waits on three external preconditions: at least one independent coordinator implementation passing the conformance suite at Level 2 (one at Level 3), peer-reviewed acceptance of the protocol at a major venue, and stewardship by a neutral foundation. The implementation supplies the substrate; the field supplies the rest.

## Citation

If you use this work, please cite:

> Ambar. (2026). *Worker Context Protocol for Mixed Workforces* (v0.955).
> Zenodo. https://doi.org/10.5281/zenodo.20367519
> [Submitted to Communications of the ACM (Research and Advances), under review]

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20367519.svg)](https://doi.org/10.5281/zenodo.20367519)

## Contact

Issues: https://github.com/Ambar-13/Worker-Context-Protocol/issues
Security: see `SECURITY.md`
Code of Conduct violations: per `CODE_OF_CONDUCT.md`
