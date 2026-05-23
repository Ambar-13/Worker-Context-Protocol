# WCP Conformance Levels

Detailed test bundle definitions for the three conformance levels in `spec/conformance.md`.

## Level 1: Protocol surface (60 tests)

Test count is approximate; suite versioning per `spec/semver-policy.md`.

### 1.1 RPC surface (9 tests, one per method)

For each of the 9 RPCs, send a syntactically valid request with valid payload; verify the response shape matches `spec/schemas/rpc-envelopes.json`.

### 1.2 Schema validation (12 tests)

Send malformed payloads against each RPC; verify `INVALID_PARAMS` (-32602) with the appropriate `data.field_path`.

### 1.3 Lifecycle transitions (10 tests)

- posted -> claimed (happy path)
- posted -> claimed (preempted; second worker)
- claimed -> executing
- claimed -> aborted (pre-execution)
- executing -> attesting
- executing -> supervising (worker-initiated)
- executing -> supervising (heartbeat timeout)
- supervising -> executing
- attesting -> settled
- attesting -> disputed (verifier fail)

### 1.4 Signature verification (5 tests)

- tasks/claim with invalid `acceptance_attestation` sig -> UNAUTHENTICATED
- tasks/claim with valid sig over wrong canonical payload -> UNAUTHENTICATED
- tasks/execute.event with invalid sig -> UNAUTHENTICATED
- tasks/attest with mismatched payload_hash and sig -> ATTESTATION_FAILED
- audit chain integrity: walk chain and verify links

### 1.5 Audit chain (5 tests)

- Each state transition emits an entry
- Hash-link integrity preserved
- Entry signed by the coordinator's audit signer
- Per-claim chain ordering is monotonic
- Tombstone pattern leaves chain verifiable

### 1.6 Heartbeat (4 tests)

- Heartbeat at 15s keeps state in `executing`
- 45s without heartbeat triggers `supervising` with `connectivity_lost`
- Reconnect with `state_snapshot` returns to `executing`
- Heartbeat after timeout but within supervision window resumes

### 1.7 Tie-break grace (3 tests)

- Two simultaneous claims; first-claim wins
- Two claims within 100ms grace; lowest bid wins
- Two claims outside grace; first-arrived wins

### 1.8 Dispute window (3 tests)

- Dispute opened within 72h transitions settled -> disputed
- Dispute opened after 72h rejected
- Dispute closes via out-of-band resolution audit entry

### 1.9 Validation gates (5 tests)

- M > N rejected at tasks/post with INVALID_ATTESTATION_REQUIREMENT
- Unknown evidence kind rejected
- x-subcontract-allowed: true rejected with SUBCONTRACT_FORBIDDEN
- Out-of-scope task class rejected with OUT_OF_SCOPE_TASK_CLASS
- Self-dealing rejected unless third-party-witness in modes

### 1.10 Idempotency (4 tests)

- tasks/post with same idempotency_key returns same task_id
- tasks/claim with same (worker, task) returns same claim_id
- tasks/attest replay returns cached verifier_decision
- tasks/settle is once per claim

## Level 2: Attestation correctness (40 tests)

Builds on Level 1.

### 2.1 Per-mode acceptance (4 tests)

For each of the 4 attestation modes, submit a well-formed evidence and verify pass.

### 2.2 Per-kind acceptance (12 tests)

For each registered kind in RFC 0003 (12 kinds at v1.0-rc1), submit a well-formed payload and verify pass.

### 2.3 Threshold evaluation (8 tests)

- `any` with one pass -> pass
- `any` with all fail -> fail
- `all` with one fail -> fail
- `all` with all pass -> pass
- `M-of-N` with M passes -> pass
- `M-of-N` with M-1 passes and one review -> review
- `M-of-N` with M-1 passes and one fail -> fail
- `M-of-N` borderline edge

### 2.4 Self-attestation gate (2 tests)

- self_attestation_with_waiver rejected without explicit task allowance
- self_attestation_with_waiver accepted with explicit allowance

### 2.5 Override audit (4 tests)

- Override applied with `override_audit_required: true` writes audit entry
- Override by unauthorized DID rejected with UNAUTHORIZED
- Override invocation surfaces in dispute audit export
- Override without `override_allowed` rejected

### 2.6 Worker-class agnosticism (10 tests)

For each of the 6 D4 cells (3 descriptors x 2 worker classes), submit a valid task and observe pass. Plus 4 cross-class invariance tests: same evidence kinds verify equivalently for human and robot workers.

## Level 3: Settlement and federation (30 tests)

Builds on Level 2.

### 3.1 Settlement state machine (8 tests)

- release captures full bond
- refund returns full bond to agent
- partial captures per partial_completion_schedule
- multi-party split sums to amount
- tasks/abort with split applies schedule
- tasks/abort with refund returns full bond
- tasks/abort with dispute parks in disputed
- dispute resolution captures or refunds per resolver decision

### 3.2 Currency and amount (4 tests)

- ISO 4217 currency code accepted
- Non-ISO currency code rejected
- Negative amount rejected
- Amount precision preserved through capture

### 3.3 Federation trust anchors (4 tests)

- Trust anchor exchange between two coordinators
- Expired trust anchor rejected
- Trust anchor revocation honored
- Asymmetric trust classes (peer accepts capability_discovery but not settlement)

### 3.4 Cross-coordinator capability discovery (4 tests)

- Federation subscribe returns peer workers with origin_coordinator
- Peer worker capabilities deduplicated correctly
- since_revision works across federation
- Federation jurisdiction refusal triggers correct error

### 3.5 Cross-coordinator task post (5 tests)

- Federated post forwards to peer
- Federated claim by peer worker captured
- Federated settlement routes back to origin coordinator's escrow
- Federated audit chain export verifiable
- Federation routing signature validated

### 3.6 Cross-coordinator reputation (5 tests)

- Reputation pointer fetched and parsed
- Signed reputation summary verified
- Stale reputation rejected
- Cross-coordinator weight applied per local policy
- Mixed own + cross reputation in matching
