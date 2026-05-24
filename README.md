# Worker Context Protocol (WCP)

**Current version:** v0.955 (architectural simplification; settlement primitives moved out of protocol)
**License:** Apache 2.0
**Schema version:** `wcp/0.2`

## What changed in v0.955

WCP v0.955 removes settlement, escrow, dispute, and refund primitives from the wire protocol. The RPC surface contracts from nine to eight (drops `tasks/settle`). The marketplace-flavoured `disputed` and `refunded` terminal states are replaced by a recheck mechanism: when the verifier rejects evidence, the worker may re-attest up to `max_attestation_attempts` times before the task voids. Marketplaces, ERPs, grant systems, and any other settlement layer subscribe to the coordinator's audit chain (`task_completed`, `task_voided`, `task_aborted`) and run their own value-flow logic. WCP is now strictly a coordination protocol. Migration guide and full change list in `spec/0.955.md`.

WCP is an open standard that coordinates AI agents and physical-world workers across institutional and industrial domains. Human technicians, autonomous robots, teleoperated systems, and hybrid worker classes share **one RPC surface**. The matching engine and the attestation verifier discriminate by **structural properties** (capabilities, evidence kinds), not by worker class.

Same algorithmic lever as the Model Context Protocol (MCP) (informational and algorithmic: in-band capability discovery plus a typed call contract), applied to physical workers rather than software tools. The primitives MCP does not need, because tools cannot fail in physically irreversible ways, are first-class: **typed attestation, supervision handoff, two-phase settlement, partial-completion abort**.

---

## Five-minute hello world (industrial-maintenance domain)

```bash
# 1. Install the CLI and SDK
pip install wcp wcp-sdk

# 2. Scaffold a worker (hybrid worker for cooling-tower thermal inspections)
wcp init worker thermal-inspector --class hybrid --domain industrial
cd thermal-inspector

# 3. Run it (CLI starts a local coordinator alongside)
pip install -r requirements.txt
wcp dev
```

In a second terminal:

```bash
# 4. Post a task to the local coordinator from the canonical industrial example
cd ../examples/agents/industrial-maintenance
python agent.py
```

You will see the coordinator log show a `tasks/post` round-trip and the worker auto-claim and attest. Five minutes from `pip install` to a hash-linked audit chain entry on disk.

To explore a different domain, swap the `--domain` flag. The 14 templates each ship handlers and attestation modes appropriate to their domain context.

---

## Six reference agents across institutionally distinct domains

The same eight RPCs handle every domain below. The variance lives in `descriptor_payload` and the registered `(mode, kind)` pairs the verifier accepts; the RPC surface is unchanged. This is the D4 forcing function proven in code.

| Domain | Path | What the agent does |
|---|---|---|
| Research operations | `examples/agents/scientific-ops/` | Schedules instrument calibration; technician on-site + signed instrument log |
| Heavy industry | `examples/agents/industrial-maintenance/` | Dispatches cooling-tower-bearing thermal inspections; hybrid human + robot workers |
| Emergency services | `examples/agents/disaster-response/` | Routes mixed drone + ground + human teams to damage zones; 3-of-5 cross-attested imagery |
| Warehouse / supply chain | `examples/agents/logistics/` | Pallet moves; AMR or human forklift operator, whichever claims first |
| Scientific field operations | `examples/agents/field-research/` | Environmental sample collection routes; GPS + signed sensor + timestamp |
| Regulated healthcare | `examples/agents/healthcare-logistics/` | Medical specimen transport; cold-chain temperature log + chain-of-custody signatures |

Each agent runs end-to-end against a local coordinator via `./run.sh` or directly via `python agent.py`.

Templates for eight additional domains (agriculture, infrastructure, manufacturing, smart-city, maritime, construction, generic, plus the six above) ship under `wcp_cli/wcp_cli/templates/`. WCP targets institutional and industrial coordination contexts.

---

## The protocol

The full normative specification is in `spec/0.2.md` (~30 pages). Companion normative documents in `spec/`:

- `threat-model.md` (STRIDE per RPC and per trust boundary)
- `privacy-architecture.md` (PII tagging, hash-only audit chain, tombstone pattern, PDPA/GDPR/CCPA alignment)
- `federation.md` (cross-coordinator capability discovery and audit chain interop)
- `conformance.md` (3 levels; the suite at `conformance/` is the canonical determinant of "WCP-conformant at Level N")
- `semver-policy.md`, `error-codes.md`, `security-baseline.md`, `time-synchronization.md`, `retry-idempotency.md`, `performance-conformance.md`
- `did-method-wcp.md` (W3C DID Core registration for `did:wcp`)
- `d4-verification-0.2.md` (six base D4 cells + four federation cells, all pass)

## Languages

| Language | Path | Package | Status |
|---|---|---|---|
| Python | `wcp_sdk_python/` | `wcp-sdk` (PyPI) | v1 + v2 decorator API; 23 tests passing |
| TypeScript | `wcp_sdk_typescript/` | `@wcp/sdk` (npm) | Worker + Agent core; Node 20+, browser-ready |
| Rust | `wcp_sdk_rust/` | `wcp-sdk` (crates.io) | Tokio async; builder pattern; for embedded workers |
| Go | `wcp_sdk_go/` | `github.com/wcp-spec/wcp-go` | Idiomatic Go: interfaces, contexts |

## LLM framework integrations

`integrations/` ships adapters for Anthropic, OpenAI, Gemini, LangChain, AutoGen, LlamaIndex, CrewAI, and the Vercel AI SDK. Each exposes the same four tools (`wcp_discover_capabilities`, `wcp_post_task`, `wcp_subscribe_attestation`, `wcp_get_audit_chain`). See `docs/llm-integration.md` for worked examples across multiple domains.

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

Opens a single-page UI at `http://localhost:8765` that connects to your coordinator's WebSocket and shows health, active tasks, audit chain tail, and RPC traffic. Read-only by default.

## Deployment

| Target | Path |
|---|---|
| Docker Compose | `deployments/docker-compose.yml` |
| Kubernetes (Helm) | `deployments/helm/wcp-coordinator/` |
| Render | `deployments/render.yaml` |
| Railway | `deployments/railway.toml` |
| Fly.io | `deployments/fly.toml` |

Before public traffic, work through `deployments/PRODUCTION_HARDENING.md`.

## Governance

- License: Apache 2.0
- `DONATION_COMMITMENT.md`: written commitment to donate stewardship to a neutral foundation by v1.0 final
- `NON_COERCION_COMMITMENT.md`: 5x integration-time ratio between WCP and non-WCP integrations
- `TRADEMARK_POLICY.md`: pre-v1.0 non-enforcement commitment
- `CHARTER.md`, `RFC_PROCESS.md`, `TSC_BYLAWS.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`

## Layout

```
spec/                       # the normative specification (v0.2)
wcp_cli/                    # `wcp` CLI + 14 domain templates
wcp_sdk_python/             # Python SDK (v1 + v2 decorator API)
wcp_sdk_typescript/         # @wcp/sdk (TypeScript)
wcp_sdk_rust/               # wcp-sdk (Rust crate)
wcp_sdk_go/                 # wcp-go (Go module)
wcp_coordinator/            # FastAPI reference backend (frozen v0.2)
wcp_worker/                 # ROS 2 Humble reference plugin (frozen v0.2)
pwa/wcp/                    # PWA module (frozen v0.2)
wcp_dev_runtime/            # `wcp dev` ASGI app wrapper
examples/agents/            # six reference agents across distinct domains
integrations/               # 8 LLM-framework adapters
inspector/                  # `wcp inspect` web UI
deployments/                # Docker Compose, Helm, Render/Railway/Fly
conformance/                # conformance suite (Python runner + Level 1-3 bundles)
operator-guide/             # RECOMMENDED practice; not normative
paper/                      # CHI 2027 + ICRA 2027 drafts
rfcs/                       # 30+ RFCs (technical + open v1.1 questions)
docs/                       # quickstarts, migration, LLM integration
```

## Pre-v1.0 final disclaimer

This is a release candidate. v1.0 final requires multiple independent implementations passing the conformance suite at Level 2 (one at Level 3), at least one external paper accepted at a major venue, and a neutral steward acceptance.

## Contact

Issues: https://github.com/Ambar-13/Worker-Context-Protocol/issues
Security: see `SECURITY.md`
Code of Conduct violations: per `CODE_OF_CONDUCT.md`
