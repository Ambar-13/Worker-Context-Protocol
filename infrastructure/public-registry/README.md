# WCP Public Coordinator Registry

A reference implementation of a publicly-queryable directory of WCP coordinators. Lets agents and workers find a coordinator to connect to by domain, jurisdiction, descriptor types accepted, supported worker classes, and conformance level.

## Why this exists

WCP is intentionally federated: there is no central directory. But a workable adoption story requires *some* mechanism for an agent built today to find a coordinator that accepts the kind of work it wants posted, in the jurisdiction where the work happens, with the conformance level the agent's operator trusts.

This service is the simplest such mechanism. It is NOT canonical: anyone can run a registry; agents can query multiple. The schema and API surface are deliberately small so a registry implementation is a weekend project.

## What the registry is

- A FastAPI service exposing JSON read endpoints and a small write surface
- A Postgres-backed store of coordinator descriptors
- A signature-verification step on every registration (coordinators sign their own descriptor)
- An optional periodic-ping prober that flags stale entries
- A simple browsable HTML index (served from the same FastAPI app) for human discovery

## What the registry is NOT

- A vetting authority. The registry verifies a coordinator's signature; it does NOT verify the coordinator's legal entity, jurisdictional claims, or operational integrity. Agents MUST do their own due diligence.
- A trust anchor. Inclusion in this registry confers no trust. Agents and workers MUST establish trust through the federation trust-anchor mechanism (RFC 0016), not by presence in any registry.
- A canonical or official directory. Multiple competing registries are expected and welcome.

## Files

- `app/main.py`: FastAPI app entry point with all routes
- `app/models.py`: SQLAlchemy ORM models
- `app/schemas.py`: Pydantic schemas for API I/O
- `app/verify.py`: signature verification on registration
- `app/prober.py`: optional liveness prober
- `app/templates/`: HTML templates for the browse view
- `schema/coordinator-descriptor.schema.json`: JSON Schema for the public descriptor format
- `docker-compose.yml`: registry + postgres
- `README.md`: this file

## Coordinator descriptor schema

A coordinator publishes a self-signed descriptor in this shape:

```json
{
  "schema_version": "wcp/0.2",
  "did": "did:wcp:example-coordinator",
  "endpoint": "wss://wcp.example.com/wcp/ws",
  "operator": "Example Operations, Ltd.",
  "operator_country": "DE",
  "operator_legal_form": "GmbH",
  "jurisdictions_served": ["DE", "AT", "CH"],
  "descriptor_types_accepted": ["transport", "inspection", "field_research"],
  "worker_classes_accepted": ["autonomous_robot", "teleoperated_system", "human"],
  "conformance_level": 3,
  "conformance_attestation_url": "https://example.com/wcp-conformance.json",
  "settlement_currencies": ["EUR", "USD"],
  "federation_peers": ["did:wcp:partner-coord-1"],
  "public_key_multibase": "z6Mk...",
  "signed_at": "2026-06-01T12:00:00Z",
  "signature": "..."
}
```

The full schema with constraints is in `schema/coordinator-descriptor.schema.json`.

## API

| Method | Path | Purpose |
|---|---|---|
| `GET /coordinators` | List coordinators with optional filters (`?country=DE&descriptor_type=transport&min_conformance=2`) |
| `GET /coordinators/{did}` | Fetch a single descriptor |
| `POST /coordinators` | Register or update (signature required) |
| `DELETE /coordinators/{did}` | Remove (signature required) |
| `GET /` | HTML browse view |
| `GET /health` | Liveness |

## Local development

```
docker compose up -d
# wait ~5 seconds
curl http://localhost:8001/health
# {"status":"healthy"}

# Register a test coordinator (signed payload)
curl -X POST http://localhost:8001/coordinators \
     -H 'Content-Type: application/json' \
     -d @sample/descriptor-signed.json
```

## Federation note

Each coordinator MAY list zero or more `federation_peers` in its descriptor. The registry does NOT verify or enforce these claims; it only echoes them. Agents wanting to use the federation_peers list as a basis for trust MUST independently verify the trust-anchor exchange per RFC 0016.

## See also

- `wcp_coordinator/` for the coordinator implementation
- `rfcs/0016-federation-primitives.md` for federation trust establishment
- `rfcs/0022-federation-discovery.md` for the federation discovery RFC (this registry is one possible implementation of the patterns in 0022)
- `infrastructure/conformance-dashboard/` for the matching conformance visualizer
