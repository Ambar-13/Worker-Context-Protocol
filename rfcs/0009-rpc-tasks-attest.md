# RFC 0009: RPC tasks/attest

- Author(s): Rentably
- Status: accepted (part of v0.1)
- Type: standards-track
- Created: 2026-05-23

## Summary

`tasks/attest` submits the worker's typed evidence for verification against the task's `attestation_requirement`.

## Design

See `spec/0.1.md` Section 3.6.

Request: `{ claim_id, attestations: AttestationEvidence[], compensating_action? }`. Response: `{ verifier_decision: "pass" | "fail" | "review", residual?, reasons? }`.

Each evidence is independently signed and verified. The aggregate verifier applies the M-of-N (or `any` / `all`) threshold across the per-mode outcomes.

**The verifier discriminates by `(mode, kind)`, NOT by worker class.** This is the load-bearing D4 win and is enforced structurally by the `attestation_verifier/` package (the SINGLE POINT of class agnosticism).

## Implementation track

`wcp_coordinator.tasks_service.attest`. Tests in `test_attestation_verifier.py` exercise both human and robot evidence kinds through identical code paths.
