# WCP Conformance Suite

The conformance suite verifies that a WCP implementation conforms to `spec/1.0-rc1.md` at the level it claims (Level 1, 2, or 3 per `spec/conformance.md`).

## Layout

```
conformance/
  README.md             # this file
  levels.md             # detailed test bundle definitions
  fixtures/             # known-good and known-bad payloads
    valid/              # payloads MUST be accepted
    invalid/            # payloads MUST be rejected with the specified error code
    edge/               # boundary conditions
  test-suite/           # language-agnostic test definitions
    level1.json
    level2.json
    level3.json
  runner-python/        # Python runner implementation
    wcp_conformance/    # the runner package
    pyproject.toml
  runner-go/            # placeholder for Go runner (v1.0-rc1 final target)
    README.md
```

## Quick start

```bash
cd conformance/runner-python
pip install -e .
wcp-conformance --target wss://impl.example.org/wcp/ws --level 1
```

## What the runner does

1. Connects to the target's JSON-RPC endpoint.
2. Runs each test case in the requested level's bundle.
3. For each case: sends the input payload, awaits the response, compares against the expected outcome.
4. Produces a structured report (`conformance-report-<timestamp>.json`) plus a human-readable summary.

The runner does NOT modify the target's database or state beyond what the test cases require. Tests use fresh DIDs and fresh task_ids per run; replay is intentional in some adversarial cases.

## What the suite does NOT certify

- Performance (see `spec/performance-conformance.md`)
- Operator policy quality (see `operator-guide/`)
- Regulatory compliance in any specific jurisdiction
- Insurance or dispute-resolution mechanisms beyond protocol contract

## Pre-v1.0 final note

The conformance suite is in active development. Test counts and exact pass criteria MAY adjust before v1.0 final. The structural form (level bundles, JSON test definitions, reproducible runs) is stable.
