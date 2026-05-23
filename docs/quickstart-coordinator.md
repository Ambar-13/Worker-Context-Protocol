# Quickstart: Run Your Own WCP Coordinator

A coordinator implements the nine WCP RPCs and operates a marketplace.

## Option 1: Local Docker Compose

```bash
git clone https://github.com/Ambar-13/Worker-Context-Protocol
cd Worker-Context-Protocol
docker compose -f deployments/docker-compose.yml up
```

Once healthy:

- Coordinator WebSocket: `ws://localhost:8000/wcp/ws`
- Coordinator HTTP health: `http://localhost:8000/wcp/health`
- Inspector UI: `http://localhost:8765`

## Option 2: Render / Railway / Fly

One-click deploy configs live at `deployments/render.yaml`, `deployments/railway.toml`, `deployments/fly.toml`. Follow each platform's deploy flow; provision a Postgres add-on and set `WCP_DATABASE_URL`.

## Option 3: Kubernetes via Helm

```bash
helm install wcp deployments/helm/wcp-coordinator/
```

See `deployments/helm/wcp-coordinator/values.yaml` for tunables.

## Option 4: Scaffold from `wcp init coordinator`

```bash
wcp init coordinator my-coordinator --port 8000
cd my-coordinator
docker compose up
```

## Production hardening

**Before public traffic, work through `deployments/PRODUCTION_HARDENING.md`.** Highlights:

- TLS termination (TLS 1.3, wss:// only)
- HSM- or KMS-backed audit-chain signing key
- NTP synchronization per `spec/time-synchronization.md`
- Rate limiting per `spec/security-baseline.md`
- OpenTelemetry observability
- Audit chain WORM storage for regulated deployments
- Federation trust-anchor exchange per `spec/federation.md`

## Conformance

After deploying, run the conformance suite against your coordinator:

```bash
wcp test --conformance --level 1 --target wss://your-coordinator.example.org/wcp/ws
```

A passing report at Level 2 or higher is the canonical "WCP-conformant" claim.

## Next steps

- `docs/quickstart-worker.md` and `docs/quickstart-agent.md` show how workers and agents connect to your coordinator.
- `operator-guide/` covers operator-side policies (reputation cold-start, dispute resolution, insurance, fraud detection, regulatory compliance, pricing).
- `spec/federation.md` describes federation with peer coordinators.
