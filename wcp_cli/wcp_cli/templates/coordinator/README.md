# {{NAME}}

WCP coordinator deployment. Runs the reference FastAPI coordinator
(`wcp_coordinator` package from PyPI) plus Postgres and Redis.

Listens on port `{{PORT}}`.

## Run locally

```bash
docker compose up
```

Once healthy, your workers connect to `ws://localhost:{{PORT}}/wcp/ws`.

## Production hardening

This compose file is dev-grade. See `deployments/PRODUCTION_HARDENING.md` in
the WCP repository for the explicit list of changes for production: TLS
termination, secret management, HSM-backed signing keys, NTP source,
backup policy, observability stack, rate limiting, federation trust anchor
exchange, and so on.

For a managed deployment, see `deployments/helm/wcp-coordinator/` for the
Kubernetes chart or the one-click platform stubs under `deployments/`.
