# wcp-conformance (Go runner)

A Go-language conformance runner for the WCP test bundle. Loads
`conformance/test-suite/level<N>.json`, opens a JSON-RPC 2.0
WebSocket to the target coordinator, runs each case, and reports
PASS / FAIL / SKIP.

The Python runner (`../runner-python/`) remains the reference. This
Go runner exists for two reasons:

1. A second-language runner shakes out implicit dependencies on the
   Python reference. If the test bundle relies on Python quirks
   (json.dumps key-order assumptions, async behavior, etc.) the Go
   port surfaces them.
2. It satisfies the four-language SDK reach claim at the conformance
   level: not just signing-and-canonical-JSON parity, but actually
   exercising the protocol surface from a non-Python runner.

## Build

```bash
cd conformance/runner-go
go build -o ./wcp-conformance-go .
```

## Run

```bash
./wcp-conformance-go --target ws://localhost:8000/wcp/ws --level 1
```

## Status (v0.955.1)

- Level 1 (protocol surface, 7 cases): all PASS against the reference
  coordinator. Verified parity with the Python runner: same cases
  pass, same cases fail.
- Level 2 (attestation correctness + recheck, 16 cases): cases with
  `expected.error_code` or `expected.result_keys` and no
  `setup_fixtures` are runnable. Cases that need multi-step flow
  setup (post → claim → attest) are reported as SKIP until the
  flow-runner extension lands.
- Level 3 (federation, 10 cases): runnable cases with simple
  `expected` shapes work. Federation-specific cases (forward,
  capability sync across coordinators) need a two-coordinator
  fixture; the in-process Python `demo.py` covers the same code
  paths and is the canonical artifact for now.

Output is a one-line-per-case PASS / FAIL / SKIP plus a summary,
exit 0 on all-pass.
