# Changelog

All notable changes to WCP are documented in this file. Format adheres to [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project follows Semantic Versioning per `spec/semver-policy.md`. The protocol identifier reported in `schema_version` is `wcp/1.0-rc1` and remains stable across all 0.x codebase tags below.

## [Unreleased]

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

No protocol surface change. All additions are additive; the `wcp/1.0-rc1` wire format is unchanged.

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

- **Vendor-neutral spec**: `spec/1.0-rc1.md` rewrites v0.1 with strict vendor neutrality. Specific operators, escrow providers, currencies, and jurisdictions appear only as examples; the spec presents them as one set of values among many.
- **New normative documents**: `spec/threat-model.md`, `spec/privacy-architecture.md`, `spec/federation.md`, `spec/conformance.md`, `spec/semver-policy.md`, `spec/error-codes.md`, `spec/security-baseline.md`, `spec/time-synchronization.md`, `spec/retry-idempotency.md`, `spec/performance-conformance.md`.
- **Extended D4 verification**: `spec/d4-verification-1.0-rc1.md` adds federation extension cells to the original 6 cells; all 10 cells use the nine RPCs unchanged.
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
