# Operator Guide: Reputation Cold-Start

**Status:** RECOMMENDED practice; not normative.

WCP defines reputation portability across coordinators (`spec/0.2.md` Section 7.1, `spec/federation.md` Section 6). The protocol does not define how reputation is bootstrapped for a new worker on a new coordinator. This document describes patterns.

## The cold-start problem

A new worker DID has zero history. The matching engine has nothing to weight. Two failure modes:

- **Over-reluctant matching**: new workers never get paired with high-value tasks; they cannot accumulate the history needed to be trusted; they leave the platform.
- **Over-permissive matching**: new workers are paired with high-value tasks; one bad actor causes a customer to lose trust in the platform.

## Pattern 1: KYC prior

For human workers, the KYC outcome serves as a strong prior. A worker who passed identity verification, has a real address, and clean AML screening is matched against tasks with bond amount up to (e.g., the operator's choice) SGD 200 on day one. The bond ceiling rises as completion history accumulates.

For robot workers, the manufacturer warranty and certifications (`required.certifications[]`) serve as the analogous prior.

## Pattern 2: Sponsor model

A new worker is sponsored by an existing high-reputation worker or by an institutional partner (e.g., a recognized contractor network). The sponsor's DID is recorded in the cold-start record. If the new worker performs poorly, the sponsor's reputation takes a small penalty. This aligns sponsor incentives with quality vouching.

Cold-start records use the audit chain:

```
event_type: "cold_start_sponsored"
payload: {
  worker_did: "did:wcp:...",
  sponsor_did: "did:wcp:...",
  sponsor_stake: "100.00 SGD",
  cold_start_at: "ISO-8601"
}
```

## Pattern 3: Cold-start work pool

The operator maintains a pool of low-stakes practice tasks (small bond, narrow attestation requirements, low-risk descriptors). New workers are routed to this pool until they accumulate (e.g.) 5 completed tasks with passing attestation. The pool MAY be operated as a subsidy (the operator absorbs some cost to bootstrap supply) or via the operator's own task generation (e.g., training data collection tasks).

## Pattern 4: Cross-coordinator import

If the worker has an established DID on a federation peer, the new coordinator MAY import the peer's reputation summary at registration time. The import is weighted per the operator's federation policy (e.g., 0.7x for newly-federated peers; 1.0x for long-standing peers). See `spec/federation.md` Section 6.

## Pattern 5: Probation

New workers begin in a probation state. During probation:

- Task bond ceiling lowered.
- Customer-facing badge displayed ("new worker").
- Disputes are resolved by the operator's ops team rather than self-service.
- Attestation thresholds are stricter (e.g., M-of-N raised to M=N for paid tasks).

Probation ends when (e.g.) 10 tasks complete with passing attestation and dispute rate below 5%.

## What WCP does NOT specify

- The numeric thresholds above. Operators choose.
- The trust class of the worker's keypair (TPM-backed vs software). The CapabilityDescriptor declares it; operators interpret.
- Whether reputation summaries should include negative events (operator policy; some operators publish only positive completions).

## Conformance note

Conformance does not require any reputation cold-start mechanism. A coordinator that bypasses cold-start (matches new workers identically to established workers) is conformant. The trade-off is operator-side risk, not protocol contract.
