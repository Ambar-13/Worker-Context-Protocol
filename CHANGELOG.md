# Changelog

All notable changes to WCP are documented in this file. Format adheres to [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project follows Semantic Versioning per `spec/semver-policy.md`.

## [Unreleased]

## [1.0-rc1] - 2026-05-23

The maximalist v1.0 release candidate. v1.0 final requires adoption validation that no single document or sprint can produce; this RC is the candidate surface and full corpus.

### Added (v1.0-rc1 over v0.1)

- **Vendor-neutral spec**: `spec/1.0-rc1.md` rewrites v0.1 with strict vendor neutrality. Specific operators, escrow providers, currencies, and jurisdictions appear only as examples; the spec presents them as one set of values among many.
- **New normative documents**: `spec/threat-model.md`, `spec/privacy-architecture.md`, `spec/federation.md`, `spec/conformance.md`, `spec/semver-policy.md`, `spec/error-codes.md`, `spec/security-baseline.md`, `spec/time-synchronization.md`, `spec/retry-idempotency.md`, `spec/performance-conformance.md`.
- **Extended D4 verification**: `spec/d4-verification-1.0-rc1.md` adds federation extension cells to the original 6 cells; all 10 cells use the nine RPCs unchanged.
- **Governance additions**: `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1), `SECURITY.md`, `TRADEMARK_POLICY.md`, `TSC_BYLAWS.md`.
- **Operator Implementation Guide**: 7 RECOMMENDED-practice documents under `operator-guide/` covering onboarding, reputation cold-start, dispute resolution, insurance partnerships, fraud detection, regulatory compliance, pricing strategies. Marked explicitly as non-normative.
- **Python SDK**: `wcp_sdk_python/` (903 LOC, 15 tests passing) with identity, RPC client, typed objects, worker and agent sessions, and an ergonomic helper for TaskDescriptor construction.
- **Conformance suite scaffold**: `conformance/` with `levels.md`, fixtures, a Python runner (`runner-python/`) installable as the `wcp-conformance` CLI, and a Go runner placeholder.
- **CHI 2027 paper draft**: `paper/chi-2027-draft.md`, full draft targeting the Sep 10, 2026 deadline.
- **RFC corpus extension**: RFCs 0013-0021 (technical, accepted) and 0022-0030 (v1.1 open questions, scoped stubs).

### Preserved unchanged from v0.1

- The nine RPCs locked at v0.1 remain the v1.0-rc1 surface.
- `spec/0.1.md`, `spec/did-method-wcp.md`, `spec/d4-verification.md` preserved at the v0.1 tag and remain readable in-tree.
- `wcp_coordinator/`, `pwa/wcp/`, `wcp_worker/` reference implementations remain operational; 44 backend tests and 8 ROS 2 host-independent tests continue to pass.

### Versioning notes

This is **v1.0-rc1**, not v1.0 final and not v2.0. v1.0 final requires multiple independent implementations passing the conformance suite at Level 2 and at least one at Level 3.

## [0.1] - 2026-05-23 (Hour 8 sprint)

Initial release. Spec under 30 pages, two reference implementations under 2000 LOC, FastAPI coordinator backend, RFCs 0000-0012, governance commitments, paper outline, coalition emails.

Tag: `v0.1` at commit f2f5869.
