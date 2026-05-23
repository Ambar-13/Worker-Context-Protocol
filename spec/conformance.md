# WCP Conformance

**Companion to:** spec/0.2.md and spec/0.955.md
**Status:** normative. Updated at v0.955: Level 3 rewritten as pure federation; settlement-related test cases removed (settlement is no longer a protocol concern).
**Compiled:** 2026-05-23

A WCP implementation is conformant at a level if it passes the corresponding test bundle in the `conformance/` suite. Conformance is determined by the suite, not by similarity to any reference implementation.

## Levels

### Level 1: Protocol surface

A Level 1 conformant implementation MUST:

1. Implement all eight RPCs with the request and response shapes in spec/0.955.md Section 1 and spec/0.2.md Section 3 (with the deltas noted in spec/0.955.md).
2. Reject malformed payloads with `INVALID_PARAMS` (-32602) and well-formed but semantically invalid payloads with the appropriate -41xxx, -42xxx, -45xxx, -46xxx, or -47xxx code per `error-codes.md`.
3. Reject `tasks/post` payloads that contain a legacy `settlement` block, or legacy `override_authority` / `override_audit_required` / `override_allowed` fields, with `INVALID_DESCRIPTOR` (-42010).
4. Accept `tasks/post` payloads that include the optional `max_attestation_attempts` and `accounting_ref` fields.
5. Verify the `acceptance_attestation` signature on every `tasks/claim` before mutating state.
6. Verify the per-event signature on every `tasks/execute` stream message before recording.
7. Emit a hash-linked signed audit chain entry on every state transition (see audit chain integrity test).
8. Enforce the 15-second heartbeat with three-missed transition to `supervising`.
9. Enforce the 100 ms tie-break grace on `tasks/claim` races.
10. Validate `attestation_requirement` against the schema registry (RFC 0003) before accepting `tasks/post`.
11. Refuse `tasks/post` with `x-subcontract-allowed: true` with `SUBCONTRACT_FORBIDDEN`.

Test count: 4 cases at this level (the core surface tests). See `conformance/test-suite/level1.json`.

### Level 2: Attestation correctness and recheck

A Level 2 conformant implementation MUST:

1. Pass Level 1.
2. Accept every registered (mode, kind) pair in RFC 0003 with well-formed payloads.
3. Reject unregistered kinds with `INVALID_ATTESTATION_REQUIREMENT`.
4. Apply `any`, `all`, and `M-of-N` thresholds correctly across permutations.
5. Reject `M > N` at `tasks/post` time.
6. Reject self-attestation with `self_attestation_with_waiver` when the task does not declare `self_attestation_explicitly_allowed=true`.
7. Implement the recheck loop per spec/0.955.md Section 3: a task with `max_attestation_attempts > 1` that fails verifier on attempt N (N < max) transitions to `rechecking`, accepts a subsequent `tasks/attest` with new evidence, increments the attempt counter, and either passes or, on exhaustion, voids.
8. Emit `attestation_attempt` and `recheck_requested` audit entries with correct attempt-number tracking.
9. Reject `tasks/attest` against a `voided` claim with `RECHECK_MAX_ATTEMPTS_REACHED` (-47001).
10. Verify that the verifier does not branch on attempt number (the same evidence at attempt 1 and attempt 3 produces the same verifier decision).
11. Honor the recheck-and-continuation pattern: a `continuation_of` block referencing a `voided` claim is accepted on a new `tasks/post`.

Test count: 13 cases at this level. See `conformance/test-suite/level2.json`.

### Level 3: Federation

A Level 3 conformant implementation MUST:

1. Pass Level 2.
2. Implement at least one federation trust class from `federation.md` (`capability_discovery`, `reputation_query`, or `audit_chain_export`).
3. Reject federation messages from peers without a current signed trust anchor.
4. Honor `federation_jurisdiction_refused` policy if declared.
5. Cross-coordinator capability discovery: a worker advertised on Coordinator B surfaces in a federated `capabilities/subscribe` on Coordinator A when the trust class is granted.
6. Cross-coordinator task post and claim: a task posted on Coordinator A with `federation: true` MAY be claimed by a worker on Coordinator B; the claim is recorded on both coordinators' audit chains.
7. Cross-coordinator audit chain interop: a `task_completed` or `task_voided` entry on Coordinator A's audit chain for a federated task is fetchable and signature-verifiable from Coordinator B via `/wcp/audit/<task_id>`.
8. Cross-coordinator recheck: a task that voids on Coordinator A may be referenced via `continuation_of` from a new task posted on Coordinator A; the continuation MAY be claimable by a worker on Coordinator B.
9. Cross-coordinator reputation: a worker DID's reputation is consistent (within the peer-policy weighting rule) when queried from either coordinator that shares a trust anchor.
10. Federation does not relax local conformance: a federated worker MUST still satisfy the local coordinator's `attestation_requirement`.

Test count: 10 cases at this level. See `conformance/test-suite/level3.json`.

Removed from Level 3 at v0.955: settlement adapter round-trip, partial-completion-schedule split disposition, cross-coordinator settlement clearing. Settlement is no longer a protocol concern.

## Test harness

The conformance suite (`conformance/`) is a language-agnostic JSON-RPC client that speaks WCP and produces a report:

```bash
$ conformance/runner-python/wcp-conformance --target wss://impl.example.org/wcp/ws --level 2
WCP Conformance Report
======================
Target:            wss://impl.example.org/wcp/ws
Schema version:    wcp/0.2
Level requested:   2
Level passed:      2

Level 1 tests:     4/4 passed
Level 2 tests:     13/13 passed
Level 3 tests:     skipped

Report:            ./conformance-report-2026-05-23T10-32-15Z.json
```

A Go-language runner is targeted for a future release (`conformance/runner-go/`). The Python runner is the reference.

## Conformance certificate

A passing implementation MAY publish the conformance report signed by the steward (post v1.0 final) or by Rentably (pre v1.0 final, under the non-enforcement commitment in `TRADEMARK_POLICY.md`). The certificate is not gated on commercial relationship; any implementer running a clean suite may publish.

## Anti-cheating

The conformance harness:

- Generates fresh randomized payloads per run so a target cannot pre-compute responses.
- Includes adversarial payloads that test failure paths, not just happy paths.
- Verifies signatures the target produces using `did_resolver` semantics; a target that returns valid-looking but unsigned audit chain entries fails the integrity test.
- Time-stamps test execution; reports include the harness version and the random seed.

## Versioning the conformance suite

Conformance level X at suite version Y is recorded in the report. A passing report against suite version 0.955 does not bind future suite versions. The steward maintains a deprecation policy for suite versions (overlap window of at least 6 months).

## What conformance does NOT certify

- Performance (see `performance-conformance.md`).
- Operator policy quality (see `operator-guide/` for recommended practice; conformance does not require any operator-guide adoption).
- Regulatory compliance in any specific jurisdiction (operator responsibility).
- Settlement, payment, escrow, refund, or dispute-mediation behaviour. These are settlement-layer concerns above WCP, not protocol concerns; the conformance suite does not exercise them.

## Reporting and registry

The steward maintains a public registry of self-reported passing implementations at `https://wcp-spec.org/registry/`. Entries are non-binding and include the implementer, the implementation name, the date passed, and the report URL. Pre-v1.0 final, Rentably maintains a placeholder registry at `https://github.com/Ambar-13/Worker-Context-Protocol/wiki/Registry`.

A vendor MAY claim "WCP-conformant at Level N" only if they have a passing report against the current suite version or a suite version within the deprecation overlap window.
