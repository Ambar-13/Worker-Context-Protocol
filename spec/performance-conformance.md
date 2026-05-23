# WCP Performance Conformance

**Companion to:** spec/1.0-rc1.md and spec/conformance.md
**Status:** normative
**Compiled:** 2026-05-23

Performance conformance is orthogonal to functional conformance (Levels 1-3 in `conformance.md`). An implementation MAY pass Level 2 functionally but declare itself "no performance tier" if it does not commit to latency budgets.

## Performance levels

### P1: Posting and matching latency

A P1-conformant implementation:

- `tasks/post` end-to-end (request received by coordinator -> response sent) at p50 < 100 ms, p99 < 500 ms.
- `capabilities/subscribe` first stream message within 250 ms of subscribe response (assuming at least one matching worker exists at subscribe time).

### P2: Attestation verification latency

A P2-conformant implementation passes P1 plus:

- `tasks/attest` verifier_decision returned at p50 < 500 ms, p99 < 2000 ms, **excluding** time spent waiting on external dependencies (third-party signature checks, biometric matching, KYC providers; these MUST be measured and reported separately).

### P3: Cross-coordinator federation latency

A P3-conformant implementation passes P2 plus:

- Federated `tasks/post` from origin to peer to acknowledgement at p50 < 500 ms, p99 < 3000 ms over a measured 50 ms RTT link.
- Federated reputation query cache-miss at p50 < 1000 ms, p99 < 5000 ms.

## Measurement methodology

Performance tests in `conformance/performance/` are run against the target implementation under a controlled load profile:

- 10 concurrent agents posting tasks at a steady rate (configurable; default 10 posts per second per agent).
- 100 concurrent workers responding to capability subscribes.
- Each task lifecycle (post -> claim -> execute (1 heartbeat) -> attest -> settle) is timed end-to-end.

Results are reported as percentile latencies aggregated over a 5-minute warm-up plus 15-minute steady-state window. The harness records:

- Latency per RPC (p50, p90, p99, p99.9)
- Throughput per RPC (per-second)
- Error rate
- Resource consumption on the target (CPU, memory, network bytes) if the target exposes Prometheus or equivalent metrics

## Reporting

A performance conformance report includes:

- Target endpoint
- Hardware profile (CPU model, RAM, network) of the target host
- Load profile (concurrent agents, workers, rps)
- The above latency tables
- A pass/fail verdict per performance level
- The audit chain integrity check pass/fail (under load, the chain MUST still link correctly)

Sample report stored at `conformance/sample-perf-report.json`.

## What performance conformance does NOT cover

- Latency to physical-world side effects (a robot navigating to a pickup pose is application-layer time, not RPC time).
- Wall-clock time of `tasks/supervise` interventions (depends on human availability).
- Settlement latency at the escrow provider (depends on the provider's SLA).
- Federation peer policy decision time (varies per peer).

## Performance regression budget

Between minor releases, no performance level's p99 may regress by more than 25%. Regressions beyond that require a `wcp:perf_regression` note in the CHANGELOG and an RFC explaining the trade-off.
