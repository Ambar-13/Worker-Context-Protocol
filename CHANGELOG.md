# Changelog

All notable changes to WCP are documented in this file. Format adheres to [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project follows Semantic Versioning per `spec/semver-policy.md`. The protocol identifier reported in `schema_version` is `wcp/0.2` and remains stable across all 0.x codebase tags below.

## [Unreleased]

## [0.955] - 2026-05-24

Architectural simplification. Settlement, escrow, dispute, and refund primitives move out of the protocol entirely. The dispute mechanism is replaced by a recheck flow on `tasks/attest`. **Breaking change from v0.95.**

### Background

WCP started as the coordination layer underneath Rentably, the marketplace that motivated it. v0.95 carried Rentably's marketplace shape: escrow, disputes, refunds, settlement at the wire layer. After the first pilot and preliminary external review, it became clear that the coordination problem WCP solves is broader than any marketplace. AI agents dispatching to humans, robots, and hybrids exists in industrial maintenance, scientific operations, disaster response, hospital logistics, defense, and research deployments that have no marketplace component at all. v0.955 removes the marketplace primitives from the protocol so it can serve those domains directly. Rentably remains a real production adopter and continues to operate its escrow and dispute system; that system now sits above WCP as one of many possible settlement layers, rather than inside it as a normative part of the protocol.

### Removed

- `tasks/settle` RPC. Calls return `METHOD_NOT_FOUND` (-32601). The protocol surface contracts from nine RPCs to eight.
- `settlement` block on the task descriptor (currency, amount, escrow_provider, split, partial_completion_schedule).
- `override_authority`, `override_audit_required`, `override_allowed` on `attestation_requirement`.
- `proposed_settlement` request field and `settlement_disposition` response field on `tasks/abort`.
- `bond_ref` envelope field on `tasks/post`.
- Terminal states `settled`, `disputed`, `refunded`. Audit entry kinds `escrow_capture`, `escrow_release`, `escrow_refund`, `settlement_split`, `federation_settlement_transfer`, `override_resolution`, `dispute_opened`, `dispute_resolved`, `refund_issued`.
- Error code range `-44xxx` (settlement errors).
- RFC 0032 (Cross-Coordinator Settlement Clearing): withdrawn.
- The `cross_coordinator_settlement` federation trust class.
- The reference coordinator's `settlement_adapter` and the `wcp_sdk.preview.federation_settlement` preview module.

### Added

- `max_attestation_attempts` (positive integer, optional, default 1) on the task descriptor.
- `accounting_ref` (opaque string, optional) on the task descriptor for external settlement-layer correlation.
- New terminal states `completed` and `voided`; intermediate state `rechecking`.
- New audit entry kinds: `task_completed`, `task_voided`, `attestation_attempt`, `recheck_requested`.
- New error codes: `-47001 RECHECK_MAX_ATTEMPTS_REACHED`, `-47002 RECHECK_NOT_AVAILABLE_FOR_TASK`, `-42010 INVALID_DESCRIPTOR` (migration guard for legacy settlement / override fields).

### Migration path (v0.95 -> v0.955)

- Agents: stop sending `settlement` block, `proposed_settlement` on abort, `bond_ref` on post. Stop calling `tasks/settle`. Subscribe to `task_completed` and `task_voided` audit entries instead. Set `accounting_ref` to the correlation token your settlement layer uses.
- Workers: implement the recheck loop on `tasks/attest` failures with `attempts_remaining > 0`.
- Coordinators: remove the `tasks/settle` handler and settlement state machine; implement the attempt counter and the recheck transitions; drop legacy settlement columns. A reference migration is in `wcp_coordinator/migrations/v0.955.py`.
- Marketplace and other settlement integrators: build settlement logic above WCP that subscribes to the audit chain.

### Notes

`wcp/0.2` schema identifier on individual typed objects is unchanged; the breaking change is a contraction of the surface and a reshape of the descriptor, not a wire-envelope rename. Adopters that key off the wire schema string for compatibility detection MUST also key off the absence of the removed fields and the changed RPC set. A future protocol-version bump may retire the `1.0-rc1` identifier; v0.955 prioritises minimal disruption to JSON-RPC envelopes for adopters partway through integration.

## [0.95] - 2026-05-23

Robot-as-agent first-class. Surfaces the pattern in which an autonomous robot's onboard controller acts as a WCP agent and dispatches follow-up tasks from inside its execute loop.

### Added

- `agent_class` enum on agent credentials (`llm_agent | embodied_agent | scheduled_agent | human_supervisor`). Informational; the matching engine and verifier do not branch on it.
- `continuation_of` metadata block on task descriptors (carries `claim_id` and `required_evidence_kinds`). Informational; preserved through federation forwarding for audit-chain continuity.
- `RobotAgent` helper in all four SDKs (Python, TypeScript, Rust, Go) wrapping the common agent-class + continuation patterns.
- Seventh reference agent: `examples/agents/delivery-robot-dispatcher/` demonstrating an AMR-to-manipulator handoff across the two new fields.
- ACM acmart-format research paper draft under `paper/` with the D4 forcing-function matrix.
- New Level 3 conformance cases covering robot-as-agent continuation and cross-coordinator `agent_class` preservation.

### Changed

- Documentation polish across docstrings, READMEs, and SDK metadata: corrected stale version strings (SDK and CLI package versions now `0.95.0`), updated the project CHANGELOG to cover every 0.x tag, and removed leftover internal sprint labels from code comments. No behavioural change.

### Notes

No protocol surface change. All additions are additive; the `wcp/0.2` wire format is unchanged.

## [0.85] - 2026-05-23

Preview implementations of v1.1 candidate features, adapter examples, registered limits, and reference agent patterns.

### Added

- Preview imports under `wcp_sdk.preview.*`: multibase identifier grammar, JCS canonical signatures, trust class extensions. All guarded behind explicit preview imports; not yet in the wire surface.
- Six adapter examples under `examples/adapters/`: MAVLink drone, MQTT IoT, VDA 5050 warehouse AMR, ROS1 compatibility shim, Modbus PLC gateway, and a vendor-robot bridge template.
- Six reference agent patterns under `examples/agents/`: logistics, healthcare-logistics, field-research, scientific-ops, industrial-maintenance, disaster-response.
- Four governance and infrastructure templates: standards-track, hosted-test-coordinator, conformance-dashboard, public-registry.

## [0.7] - 2026-05-23

Consolidated hardening. Spec clarifications, additional conformance fixtures, and SDK polish across all four languages. No protocol surface change.

## [0.55] - 2026-05-23

Comment-only maintenance patch. No behavioral change.

## [0.5] - 2026-05-23

Developer-adoption infrastructure.

### Added

- `wcp` CLI (`wcp_cli/`) with 14 domain templates covering institutional and industrial coordination contexts.
- LLM-framework integrations under `integrations/` for Anthropic, OpenAI, Gemini, LangChain, AutoGen, LlamaIndex, CrewAI, and the Vercel AI SDK.
- Visual inspector (`inspector/`) served at `http://localhost:8765` and launched via `wcp inspect`.
- Deployment configurations under `deployments/` for Docker Compose, Helm, Render, Railway, and Fly.io.

## [0.2] - 2026-05-23

The maximalist release candidate for v1.0. v1.0 final requires adoption validation that no single document can produce; this tag carries the candidate surface and full normative corpus.

### Added (over v0.1)

- **Vendor-neutral spec**: `spec/0.2.md` rewrites v0.1 with strict vendor neutrality. Specific operators, escrow providers, currencies, and jurisdictions appear only as examples; the spec presents them as one set of values among many.
- **New normative documents**: `spec/threat-model.md`, `spec/privacy-architecture.md`, `spec/federation.md`, `spec/conformance.md`, `spec/semver-policy.md`, `spec/error-codes.md`, `spec/security-baseline.md`, `spec/time-synchronization.md`, `spec/retry-idempotency.md`, `spec/performance-conformance.md`.
- **Extended D4 verification**: `spec/d4-verification-0.2.md` adds federation extension cells to the original 6 cells; all 10 cells use the nine RPCs unchanged.
- **Governance additions**: `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1), `SECURITY.md`, `TRADEMARK_POLICY.md`, `TSC_BYLAWS.md`.
- **Operator Implementation Guide**: 7 RECOMMENDED-practice documents under `operator-guide/` covering onboarding, reputation cold-start, dispute resolution, insurance partnerships, fraud detection, regulatory compliance, and pricing strategies. Marked explicitly as non-normative.
- **Python SDK**: `wcp_sdk_python/` with identity, RPC client, typed objects, worker and agent sessions, and an ergonomic helper for TaskDescriptor construction.
- **Conformance suite scaffold**: `conformance/` with `levels.md`, fixtures, a Python runner (`runner-python/`) installable as the `wcp-conformance` CLI, and a Go runner placeholder.
- **Research paper draft**: full draft under `paper/` targeting an external venue.
- **RFC corpus extension**: RFCs 0013-0021 (technical, accepted) and 0022-0030 (v1.1 open questions, scoped stubs).

### Preserved unchanged from v0.1

- The nine RPCs locked at v0.1 remain the surface.
- `spec/0.1.md`, `spec/did-method-wcp.md`, `spec/d4-verification.md` preserved at the v0.1 tag and remain readable in-tree.
- `wcp_coordinator/`, `pwa/wcp/`, `wcp_worker/` reference implementations remain operational; their test suites continue to pass.

### Versioning notes

This codebase predates v1.0 final, which requires multiple independent implementations passing the conformance suite at Level 2 and at least one at Level 3.

## [0.1] - 2026-05-23

Initial release. Spec under 30 pages, two reference implementations under 2000 LOC, FastAPI coordinator backend, RFCs 0000-0012, governance commitments, paper outline.
