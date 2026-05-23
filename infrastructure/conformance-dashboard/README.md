# WCP Conformance Dashboard

A reference UI for displaying WCP conformance test results across implementations. Operators, integrators, and prospective users open the dashboard to see which coordinator implementations have passed Level 1, 2, or 3 of the conformance suite, when, against which test version, and with what notes.

## Why this exists

The conformance test suite (`conformance/test-suite/level{1,2,3}.json`) is machine-runnable, but humans need a visualization. Without a dashboard, "is X coordinator Level 3?" is answered by reading a JSON file in a GitHub repo, which is friction the ecosystem can do without.

This dashboard is the reference visualization. It is NOT canonical: anyone may run a dashboard; implementations may self-publish results that the dashboard ingests via a small JSON manifest.

## What this directory contains

- `data-schema/conformance-result.schema.json`: the JSON Schema for a single conformance result a coordinator publishes
- `data-schema/dashboard-aggregate.schema.json`: the shape of the dashboard's own aggregated view across implementations
- `mockups/dashboard.html`: a static HTML mockup of the dashboard UI (renders sample data; intended as a design reference for a real frontend implementation)
- `mockups/coordinator-detail.html`: a single-coordinator detail view mockup
- `sample-data/`: example result manifests for three fictional coordinators (Levels 1, 2, 3)
- `README.md`: this file

The actual web frontend implementation (React/Svelte/etc.) is out of scope for the v1.0-rc4 sprint; the deliverable here is the schema + mockup that fixes the contract a frontend would build against.

## Data flow

```
+-----------------+         +------------------+         +------------------+
| coordinator     |  POST   |  conformance     |  GET    |  dashboard       |
| (publisher)     |-------->|  result manifest |-------->|  frontend        |
+-----------------+         |  (host: own URL  |         +------------------+
                            |   or registry)   |
                            +------------------+
```

A coordinator publishes a self-signed conformance result manifest at a stable URL. The dashboard discovers manifests by:

1. Polling the public coordinator registry (`infrastructure/public-registry`) and reading each entry's `conformance_attestation_url` field
2. OR accepting direct submission of a manifest URL through the dashboard's own admin surface (operator-side)
3. OR ingesting a flat list of manifest URLs from a config file (operator-managed list)

The dashboard does NOT execute the conformance suite. It DISPLAYS results published by coordinator implementations that ran the suite themselves (or had a third party run it).

## Trust model

The dashboard verifies the manifest's signature against the coordinator's published key (same key it uses to register with the public registry). The dashboard does NOT validate that the conformance suite was actually run; it trusts the publisher's self-report.

For a higher trust level, operators can:

- Require third-party-witnessed conformance results (the manifest references a witness DID and signature)
- Use the conformance suite's `level3` jurisdictional-fixtures evidence to cross-check the publisher's claims
- Cross-reference against community-run conformance against the same coordinator

The dashboard exposes the manifest's signature and provenance fields so consumers can apply their own trust criteria.

## Conformance levels (reference)

| Level | Scope |
|---|---|
| 1 | Core protocol mechanics (RPC shapes, schema, basic capability matching) |
| 2 | Federation + audit chain + override authority semantics |
| 3 | Jurisdictional fixtures (data-residency, settlement, dispute resolution under sample real-world law) |

Detailed level definitions are in `conformance/test-suite/`.

## See also

- `conformance/test-suite/level1.json`, `level2.json`, `level3.json`
- `infrastructure/public-registry/` for the companion registry
- `infrastructure/hosted-test-coordinator/` for a runnable coordinator that produces results
- `rfcs/0013-conformance-suite.md` for the conformance suite RFC
