# wcp-conformance (Go runner)

Placeholder for the Go-language conformance runner. The Python runner (`../runner-python/`) is the v0.2 reference; the Go runner is targeted for v0.2 final.

## Sketch

A Go implementation will:

1. Load `level<N>.json` from `../test-suite/`.
2. Open a JSON-RPC 2.0 WebSocket to the target.
3. Run each case (parameter materialization with `{{key}}` substitution; check expected outcome).
4. Produce a JSON report identical in shape to the Python runner's.

## Why two runners

A second-language runner shakes out implicit dependencies on the Python reference. If the test bundle relies on quirks of the Python runner, the Go port surfaces them. Cross-language runners are a published practice (W3C WPT, OpenID conformance suites; both maintain >1 runner) [reasoned].
