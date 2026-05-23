# WCP Time Synchronization

**Companion to:** spec/0.2.md
**Status:** normative
**Compiled:** 2026-05-23

Time-sensitive operations in WCP include: heartbeat timeout (15s with 3-missed transition), claim tie-break grace (100 ms), claim-expiry (operator-defined; 72-hour default from the most recent state change), expiry checks on `tasks/post`, replay protection on `acceptance_attestation` (5 minutes), and audit chain timestamps. Clock drift across workers, coordinators, and federation peers can cause misclassification of these events.

## 1. Canonical time source

Every WCP coordinator MUST declare a canonical time source and publish it in its `did:wcp` document under `wcp:metadata.canonical_time_source`. Acceptable values:

- `coordinator_local_ntp`: the coordinator's NTP-synced local clock (the default)
- `nist`: time.nist.gov stratum 1 servers
- `cloudflare`: time.cloudflare.com (Roughtime)
- `pool.ntp.org`: the NTP pool
- `tai_offset_from_utc`: a TAI-based source with the leap-second policy declared

A coordinator's audit chain timestamps come from the coordinator's canonical time source. Worker timestamps in events come from the worker's own clock and MAY drift; the coordinator's `received_at` is authoritative.

## 2. Drift tolerance

| Operation | Tolerance |
|---|---|
| acceptance_attestation `signed_at` vs coordinator time | -5 minutes to +30 seconds; outside this band, reject with -40001 |
| evidence `collected_at` vs coordinator time | -24 hours to +5 minutes; older than -24h flagged for review |
| heartbeat event timestamp | -2 minutes to +30 seconds |
| audit chain entry `prev_hash` -> `this_hash` order | monotonic non-decreasing within a claim_id |

## 3. NTP requirements

Coordinators MUST be NTP-synced. SHOULD use at least 3 NTP sources with stratum <= 3. Coordinators SHOULD log NTP offset every 60 seconds; offsets > 100 ms warrant alerting.

Workers (robots and PWAs) SHOULD synchronize their clocks to NTP or a comparable source. PWAs running in a browser inherit the device clock; the PWA MUST display a warning when the device clock differs from the coordinator's canonical time by more than 5 minutes.

## 4. Timestamp authority for the audit chain

Audit chain `timestamp` is set by the coordinator at append time using the coordinator's canonical time source. Workers MAY include their own timestamps in event payloads; these are advisory.

Conformance Level 1 verifies that the audit chain's `timestamp` ordering is monotonic per claim_id (i.e., `timestamp_n >= timestamp_(n-1)` for entries n in the chain).

## 5. Cross-coordinator federation

Federation peers SHOULD reconcile time differences:

- Trust anchors include `issued_at`; peers verify the trust anchor is current per local policy.
- Cross-coordinator audit chain export carries the source coordinator's timestamps verbatim; the consumer MAY note skew vs its own clock.

## 6. Leap seconds

UTC includes leap seconds. WCP timestamps are UTC ISO-8601. Coordinators MUST follow either:

- **Smear over 24 hours**: distribute the leap second across a 24-hour window (the Google approach [verified]); favored for production stability.
- **Strict UTC**: reflect the leap second in real time and accept that timestamps may appear to repeat or skip.

The choice is declared in `wcp:metadata.leap_second_policy` on the coordinator's DID document.

## 7. Daylight saving time and time zones

All wire-format timestamps are UTC ISO-8601 with the `Z` suffix or `+00:00`. Local-time presentation (in PWAs, dashboards, audit exports) is the operator's responsibility.

`available_windows[].timezone` on capability descriptors is an IANA Time Zone Database name (for example, `Asia/Singapore`, `Europe/London`, `America/Los_Angeles`).

## 8. Clock recovery after disconnect

A worker that disconnects and reconnects MUST re-anchor its event timestamps to the coordinator's canonical time on reconnect. The worker MAY estimate its drift from coordinator-acknowledged events.

## 9. What WCP does NOT mandate

- No specific NTP provider.
- No millisecond-precision UTC source (`time-synchronization.md` requires only ~100 ms accuracy).
- No clock attestation hardware (TPM-backed time is acceptable but not required).
