# WCP Conformance

**Companion to:** spec/1.0-rc1.md
**Status:** normative
**Compiled:** 2026-05-23

A WCP implementation is conformant at a level if it passes the corresponding test bundle in the `conformance/` suite. Conformance is determined by the suite, not by similarity to any reference implementation.

## Levels

### Level 1: Protocol surface

A Level 1 conformant implementation MUST:

1. Implement all nine RPCs with the request and response shapes in spec/1.0-rc1.md Section 3.
2. Reject malformed payloads with `INVALID_PARAMS` (-32602) and well-formed but semantically invalid payloads with the appropriate -41xxx, -42xxx, -45xxx, or -46xxx code per `error-codes.md`.
3. Verify the `acceptance_attestation` signature on every `tasks/claim` before mutating state.
4. Verify the per-event signature on every `tasks/execute` stream message before recording.
5. Emit a hash-linked signed audit chain entry on every state transition (see audit chain integrity test).
6. Enforce the 15-second heartbeat with three-missed transition to `supervising`.
7. Enforce the 100 ms tie-break grace on `tasks/claim` races.
8. Honor the 72-hour `dispute_window` default.
9. Validate `attestation_requirement` against the schema registry (RFC 0003) before accepting `tasks/post`.
10. Refuse `tasks/post` with `x-subcontract-allowed: true` with `SUBCONTRACT_FORBIDDEN`.

Test count: ~60 tests. See `conformance/test-suite/level1.json`.

### Level 2: Attestation correctness

A Level 2 conformant implementation MUST:

1. Pass Level 1.
2. Accept every registered (mode, kind) pair in RFC 0003 with well-formed payloads.
3. Reject unregistered kinds with `INVALID_ATTESTATION_REQUIREMENT`.
4. Apply `any`, `all`, and `M-of-N` thresholds correctly across permutations.
5. Reject `M > N` at `tasks/post` time.
6. Reject self-attestation with `self_attestation_with_waiver` when the task does not declare `self_attestation_explicitly_allowed=true`.
7. Audit-chain every override invocation with `override_audit_required=true`.

Test count: ~40 tests. See `conformance/test-suite/level2.json`.

### Level 3: Settlement and federation

A Level 3 conformant implementation MUST:

1. Pass Level 2.
2. Round-trip a `tasks/settle` decision against an escrow adapter (the conformance harness ships a fake adapter for testing).
3. Apply `partial_completion_schedule` correctly on `tasks/abort` with `split` disposition.
4. Implement at least one federation trust class from `federation.md` (capability_discovery, reputation_query, audit_chain_export, or cross_coordinator_settlement).
5. Reject federation messages from peers without a current signed trust anchor.
6. Honor `federation_jurisdiction_refused` policy if declared.

Test count: ~30 tests. See `conformance/test-suite/level3.json`.

## Test harness

The conformance suite (`conformance/`) is a language-agnostic JSON-RPC client that speaks WCP and produces a report:

```bash
$ conformance/runner-python/wcp-conformance --target wss://impl.example.org/wcp/ws --level 2
WCP Conformance Report
======================
Target:            wss://impl.example.org/wcp/ws
Schema version:    wcp/1.0-rc1
Level requested:   2
Level passed:      2

Level 1 tests:     60/60 passed
Level 2 tests:     40/40 passed
Level 3 tests:     skipped

Report:            ./conformance-report-2026-05-23T10-32-15Z.json
```

A Go-language runner is targeted for v1.0-rc1 final (`conformance/runner-go/`). The Python runner is the v1.0-rc1 reference.

## Conformance certificate

A passing implementation MAY publish the conformance report signed by the steward (post v1.0 final) or by Rentably (pre v1.0 final, under the non-enforcement commitment in `TRADEMARK_POLICY.md`). The certificate is not gated on commercial relationship; any implementer running a clean suite may publish.

## Anti-cheating

The conformance harness:

- Generates fresh randomized payloads per run so a target cannot pre-compute responses.
- Includes adversarial payloads that test failure paths, not just happy paths.
- Verifies signatures the target produces using `did_resolver` semantics; a target that returns valid-looking but unsigned audit chain entries fails the integrity test.
- Time-stamps test execution; reports include the harness version and the random seed.

## Versioning the conformance suite

Conformance level X at suite version Y is recorded in the report. A passing report against suite version 1.0-rc1 does not bind future suite versions. The steward maintains a deprecation policy for suite versions (overlap window of at least 6 months).

## What conformance does NOT certify

- Performance (see `performance-conformance.md`).
- Operator policy quality (see `operator-guide/` for recommended practice; conformance does not require any operator-guide adoption).
- Regulatory compliance in any specific jurisdiction (operator responsibility).
- Insurance, dispute-resolution, or fraud-detection mechanisms beyond the protocol contract.

## Reporting and registry

The steward maintains a public registry of self-reported passing implementations at `https://wcp-spec.org/registry/`. Entries are non-binding and include the implementer, the implementation name, the date passed, and the report URL. Pre-v1.0 final, Rentably maintains a placeholder registry at `https://github.com/Ambar-13/Worker-Context-Protocol/wiki/Registry`.

A vendor MAY claim "WCP-conformant at Level N" only if they have a passing report against the current suite version or a suite version within the deprecation overlap window.
