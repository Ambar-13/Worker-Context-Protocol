# WCP Hosted Test Coordinator

A production-shaped Docker Compose stack for running a public-facing WCP test coordinator. Designed for organizations that want to offer "try WCP without standing up your own coordinator" as a 1-click experience to prospective workers, agents, and adapter authors.

## Why this exists

Adoption of a new protocol is gated on the friction of getting a first task to flow end-to-end. A hosted test coordinator removes that friction: a developer can point an agent or worker at `wss://test.<your-org>.example/wcp/ws`, post or claim a task, and see the audit chain entry appear in a public dashboard within minutes.

This directory is the deployment scaffold for such a service. It is NOT a managed service; the operator runs and pays for it.

## What is here

| File | Purpose |
|---|---|
| `docker-compose.yml` | Service composition: coordinator, postgres, redis, traefik, prometheus, grafana |
| `config/coordinator.toml` | Coordinator configuration with sensible test-mode defaults |
| `config/traefik.yml` | Reverse proxy + TLS termination via ACME |
| `config/prometheus.yml` | Metrics scraping |
| `config/grafana-datasource.yml` | Grafana auto-provisioning |
| `dashboards/wcp-overview.json` | Pre-built Grafana dashboard for coordinator metrics |
| `secrets/.env.example` | Environment variables (real `.env` is operator-side, not committed) |
| `init/01-create-db.sql` | Postgres schema bootstrap |
| `Makefile` | Common operations (`make up`, `make rotate-keys`, `make wipe`) |

## Quick start (operator)

```
# 1. Clone this repo, cd to infrastructure/hosted-test-coordinator/
cp secrets/.env.example secrets/.env
$EDITOR secrets/.env   # set TLS domain, secrets, escrow provider

# 2. Bring up
make up

# 3. First-time-only schema init (idempotent)
make migrate

# 4. Check health
curl https://test.<your-org>.example/health
# -> {"status":"healthy","coordinator_did":"did:wcp:test-<your-org>","version":"v0.95"}

# 5. Open Grafana
open https://test.<your-org>.example/grafana
```

## What "production-shaped" means here

This stack is production-*shaped* but the test coordinator's policies are NOT suitable for value-bearing tasks:

- **Settlement** is configured to a sandbox-only escrow provider that does not move real money. The provider returns scripted responses for `capture` and `refund`.
- **Trust anchors** are open: any DID may register as an agent or worker. No KYC, no vetting.
- **Retention** of audit chain entries is 30 days. After that, entries are pruned. Operators wanting forensic retention must run their own coordinator.
- **Rate limits** are aggressive (10 task posts per agent per minute) to keep the shared environment usable.

A real production deployment hardens all four areas. The stack here keeps the structure (auth, settlement adapter, audit chain, rate limiting are all present and configured) so the rollout path to production is a configuration change, not an architecture rewrite.

## Service overview

```
                          +-------------------+
                          |     Traefik       |
                          |  TLS + routing    |
                          +---------+---------+
                                    |
                +-------------------+---------+----------------+
                |                             |                |
        +-------v--------+         +----------v-----+   +------v------+
        |   Coordinator  |         |     Grafana    |   |  Prometheus |
        |   (FastAPI)    |         +----------+-----+   +------+------+
        +-------+--------+                    |                |
                |                             +<---scrape------+
        +-------v-------+
        |   Postgres    |
        +---------------+
                |
        +-------v-------+
        |     Redis     | (claim locks, rate limit counters)
        +---------------+
```

## Security posture (test mode)

| Concern | Test mode |
|---|---|
| TLS | Required (Let's Encrypt via Traefik ACME) |
| Coordinator-to-DB | Postgres password from `.env`; bind to localhost only |
| Worker/agent auth | DID + Ed25519 signature on connection challenge; no allowlist |
| Settlement | Sandbox escrow only |
| Audit chain backup | Daily `pg_dump` to a configurable S3 / Object Storage bucket |
| Key rotation | `make rotate-keys` generates a new coordinator signing key and starts a key-overlap window |

## Wiping the deployment

```
make wipe   # stops services + removes volumes + removes generated keys
```

This is destructive and intended for test environments. Do not run in production.

## Capacity sizing (REASONED, sandbox load)

The default Compose file targets a small VM (2 vCPU, 4 GB RAM, 50 GB SSD). Empirical sandbox load on this footprint:

- Sustained: ~50 concurrent workers, ~5 tasks/sec
- Peak: ~150 concurrent workers, ~20 tasks/sec for short bursts

Operators running larger test deployments should scale postgres + redis vertically before scaling the coordinator container horizontally.

## See also

- `wcp_coordinator/` (the coordinator source code)
- `infrastructure/public-registry/` (companion registry for discovering coordinators)
- `infrastructure/conformance-dashboard/` (visualizer for compliance results)
- `docs/limits/failure-modes.md` for the failure catalog operators should plan around
