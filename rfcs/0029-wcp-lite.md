# RFC 0029: WCP-Lite for Intermittent Connectivity

- Author(s): TBD
- Status: open (v1.1 exploratory)
- Type: experimental
- Created: 2026-05-23
- Targets: v1.1 or v2.0

## Summary

A subset of WCP for workers with intermittent connectivity (rural delivery contractors, robots in subterranean spaces, maritime workers). Worker can claim, execute, and stage attestation evidence offline; flushes on reconnect.

## Motivation

The 15-second heartbeat assumes near-continuous connectivity. Some real-world contexts have hours of offline time per task. The current spec handles this via `tasks/supervise(connectivity_lost)` followed by resume, but the experience is awkward and reliant on supervisor goodwill.

## Open design questions

- Whether the offline subset should be a separate "Lite" profile or a runtime mode of the full protocol.
- How to handle attestation evidence collected offline whose `collected_at` is more than 24 hours stale on reconnect.
- Cross-coordinator federation when both parties are intermittently online.

## Implementation track

v1.1 or v2.0. Significant design work; not a quick add.
