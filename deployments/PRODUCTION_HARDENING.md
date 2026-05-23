# Production Hardening Checklist

The `deployments/docker-compose.yml` and the per-template `coordinator` scaffold
are **dev-grade**. Before running a WCP coordinator against production traffic,
apply the changes in this checklist.

## 1. TLS termination

- Run the coordinator behind a TLS-terminating proxy (nginx, Caddy, Traefik,
  or a managed load balancer).
- Use TLS 1.3 minimum per `spec/security-baseline.md`.
- The coordinator's public WebSocket endpoint MUST be `wss://`, not `ws://`.
- HTTP-only is acceptable only on the loopback interface during development.

## 2. Secrets and signing keys

- The coordinator's audit-chain signing key MUST be stored in an HSM or KMS
  in production. The reference uses an in-process Ed25519 key for tests.
- Database credentials, Stripe (or alternative escrow) API keys, and any
  third-party tokens belong in a secret manager (HashiCorp Vault, AWS Secrets
  Manager, Google Secret Manager, sealed-secrets for k8s).
- Worker DID private keys belong on the worker device, not in the coordinator.

## 3. Database

- Use a managed Postgres or self-hosted with regular backups.
- Enable point-in-time recovery (PITR).
- Schedule daily logical backups (`pg_dump`) tested by restore.
- Set up replicas for read-heavy workloads (audit chain tail, capability list).

## 4. Time source

- The coordinator MUST be NTP-synced per `spec/time-synchronization.md`.
- Declare the canonical time source in the coordinator's DID document under
  `wcp:metadata.canonical_time_source`.
- Use the smear policy for leap seconds (`wcp:metadata.leap_second_policy:
  smear`) for production stability.

## 5. Rate limiting

- Apply per-DID rate limits per `spec/security-baseline.md` Section 7.
- Defaults: capabilities/list 60 per min per worker; tasks/post 60 per min
  per agent; tasks/claim 600 per min per worker.
- Use a request-counting middleware (nginx, Envoy, Kong, or app-level) that
  honors the `X-WCP-Worker-DID` and `X-WCP-Agent-DID` headers.

## 6. Observability

- Stand up Prometheus + Grafana (or alternative).
- Coordinator MUST emit OpenTelemetry traces for each RPC and for each audit
  chain append.
- Log structured JSON with correlation IDs; ingest into a SIEM or log lake.
- Alert on: signature verification failure rate, rate-limit triggers,
  heartbeat-timeout-to-supervising transitions, and audit chain integrity
  check failures.

## 7. Audit chain durability

- Audit entries are append-only and tamper-evident. Production deployments
  SHOULD also write entries to a write-once-read-many (WORM) store for
  regulatory deployments.
- Schedule chain integrity checks (the `verify_chain` semantics in the
  reference) at least daily, with alerts on any failure.

## 8. Federation

- Federation trust anchors are bilateral and signed. Manage anchor rotation
  per a documented quarterly cadence.
- Anchors live in a coordinator-side store. Backup and recovery for that
  store is the same priority as the database.

## 9. Worker-class scope and refusal

- The reference coordinator refuses out-of-scope task classes (medical,
  defense, minor-involving, hazmat-above-consumer) by default. Production
  deployments that need to relax these MUST publish an explicit operator
  policy and an RFC review.

## 10. Conformance

- Run `wcp test --conformance --level 1` against the deployment as a smoke
  test in your CI pipeline.
- Run Level 2 in pre-production at least weekly.
- Publish a conformance report URL per the `TRADEMARK_POLICY.md` rules
  before claiming "WCP-conformant at Level N".

## 11. Backups and disaster recovery

- Document RTO and RPO targets.
- Test full coordinator restore from backup at least quarterly.
- Federation peers SHOULD honor audit-chain export requests during DR.

## 12. Personnel and operations

- TSC and operator-side incident response are separate. Document who is
  on-call for the coordinator vs who handles spec-level questions.
- Security disclosure follows `SECURITY.md` SLA.
