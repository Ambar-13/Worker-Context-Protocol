# Worker Context Protocol: W3C Technical Contribution

**Document classification:** W3C Member Submission technical contribution
**Submitting organization:** [PRINCIPAL TO PROVIDE: W3C member organization]
**Document version:** 1.0-rc3
**License:** W3C Document License (per W3C Process Document Section 7.4); underlying WCP code Apache 2.0

---

## Abstract

The Worker Context Protocol (WCP) is an open protocol that coordinates AI agents and physical-world workers through one RPC surface. Workers may be humans, autonomous robots, teleoperated systems, semi-autonomous platforms, or hybrid worker classes; the protocol's matching engine and attestation verifier discriminate by structural properties (capabilities, evidence kinds), not by worker class. This document positions WCP as a candidate W3C-track standard: the `did:wcp` DID method anchors identity (built on W3C DID Core), the typed attestation primitive interoperates with Verifiable Credentials and the Data Integrity model, and the federation layer demonstrates a concrete pattern for cross-organization trust in agent-and-worker workflows.

## 1. Introduction

WCP addresses the protocol-layer coordination problem between AI agents (capable of dispatching physical-world work) and workers (entities that execute it). The protocol fits a gap between agent-platform-specific tool protocols (e.g., the Model Context Protocol for software tools) and physical-world coordination protocols (e.g., VDA 5050 for warehouse fleets), serving the case where AI-driven dispatch must work across worker classes (humans, robots, hybrids) and across institutional contexts (industrial, scientific, healthcare-logistics, emergency-response, research, manufacturing, smart-city, maritime, construction, agricultural, infrastructure).

WCP is designed under the lever of MCP (informational and algorithmic: in-band capability discovery plus a typed call contract), applied to physical workers rather than software tools, with first-class primitives that MCP does not need because tools cannot fail in physically irreversible ways: typed attestation, supervision handoff, two-phase settlement, partial-completion abort.

## 2. Relationship to W3C technical work

WCP intersects with W3C Recommendations and Working Drafts in three areas:

### 2.1 Decentralized Identifiers (DID Core)

WCP defines a new DID method, `did:wcp`. The method spec is `spec/did-method-wcp.md` in the WCP repository. It is built on W3C DID Core 1.0, supports Ed25519 as the initial signing algorithm, and uses base58btc encoding (with a v1.1 migration to multibase per WCP RFC 0031 to align with `did:key` and similar W3C-tracked methods).

`did:wcp` identifiers serve three roles in the protocol:
- Worker identity
- Operator identity
- Coordinator identity (for federation trust anchors)

The method registration request is in the companion document `did-method-registration-request.md`.

### 2.2 Verifiable Credentials and Data Integrity

WCP's audit chain is structurally analogous to a Verifiable Credential chain with hash-linked integrity. Each audit chain entry is a signed claim about a state transition; the chain's hash structure provides tamper-evidence equivalent to a VC's proof. WCP RFC 0034 (External Trust-Root Signed Evidence) defines a pattern where evidence signed against external trust roots (X.509 chains, JWKS endpoints, non-`did:wcp` DIDs) is registered as a typed evidence kind and verified natively without bridging through a `did:wcp` re-sign. This pattern is conceptually adjacent to the VC Data Integrity work and to SCITT (IETF working group).

We see potential alignment with the Verifiable Credentials Working Group around:
- Standardizing the audit chain entry's JSON-LD context (currently a plain JSON object with `schema_version`)
- Bridging VC presentations into WCP attestation evidence as a registered evidence kind

### 2.3 DID Resolution

`did:wcp` resolution is currently bilateral between WCP coordinators (each coordinator hosts a DID resolver for its registered workers). The W3C DID Resolution specification provides a useful framework; we may align resolution responses with the DID Resolution data model in v1.1 or v1.2.

## 3. Concrete contribution

We contribute:

1. **`did:wcp` method specification** for inclusion in the W3C DID method registry.
2. **A worked-out audit chain model** with reference implementations (Python, TypeScript, Rust, Go) demonstrating how DID-anchored signed claims compose into a tamper-evident chain.
3. **A federation model** that does not require a global trust anchor; bilateral trust anchors are explicit, signed, and discoverable.
4. **A conformance suite** covering protocol surface, attestation correctness, and federation (three levels, with concrete test cases).
5. **A worked-out attestation primitive** with M-of-N threshold logic, four mode classes (sensor-witness, third-party-witness, cryptographic-presence, owner-sign-off), and an extension point for external trust roots.

## 4. Open questions for W3C consideration

1. **DID method registration disposition.** We request review of `did:wcp` for inclusion in the DID method registry. The companion `did-method-registration-request.md` provides the formal request.

2. **WG affiliation.** Where (if anywhere) does `did:wcp` and the agent-and-worker coordination model best fit? Candidates: DID WG, Verifiable Credentials WG, Web of Things WG, or a new WG specifically for AI agents and physical-world coordination.

3. **Liaison with adjacent work.** WCP federation maps closely to IETF SCITT (Supply Chain Integrity, Transparency, and Trust). A formal liaison (W3C-IETF) may benefit both efforts.

4. **VC-WCP bridge specification.** If the Verifiable Credentials WG is interested, we propose a small bridge specification: a registered evidence kind in WCP that accepts a VC Presentation as the underlying evidence, with the issuing DID serving as the external trust root per WCP RFC 0034.

## 5. Project governance and stewardship

WCP's donating organization commits to donate stewardship to Linux Foundation Projects LLC before v1.0 final (`DONATION_COMMITMENT.md` in the repository). The W3C engagement is independent of LF stewardship; post-donation, the LF-stewarded project continues to engage W3C as appropriate.

Governance documents in the repository:

- `GOVERNANCE.md`, `CHARTER.md`, `TSC_BYLAWS.md`
- `RFC_PROCESS.md` with 34+ RFCs drafted or accepted
- `TRADEMARK_POLICY.md` with non-enforcement commitment pre-LF-acceptance
- `NON_COERCION_COMMITMENT.md` with 5x maximum integration-time ratio
- `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1)
- `CONTRIBUTING.md` (Developer Certificate of Origin, no CLA)
- `SECURITY.md` (vulnerability disclosure policy)

## 6. License terms

- WCP source code, reference implementations, conformance suites, and RFCs: Apache 2.0.
- This submission document and the companion `did-method-registration-request.md`: W3C Document License (per W3C Process Document Section 7.4) plus Apache 2.0 for derivative works.
- `did:wcp` method specification (`spec/did-method-wcp.md`): Apache 2.0 in the repository; W3C Document License applies to any verbatim reproduction in W3C technical reports.

## 7. References

Normative:

- W3C DID Core 1.0 (https://www.w3.org/TR/did-core/) [VERIFIED]
- W3C Verifiable Credentials Data Model 1.1 (https://www.w3.org/TR/vc-data-model/) [VERIFIED]
- IETF RFC 7515 (JOSE/JWS), RFC 7517 (JWK), RFC 7518 (JWA) [VERIFIED]

Informative:

- Model Context Protocol (https://modelcontextprotocol.io/) [VERIFIED]
- VDA 5050 Open Source Reference Implementation [REASONED]
- IETF SCITT WG (https://datatracker.ietf.org/wg/scitt/) [VERIFIED]
- WCP repository (https://github.com/Ambar-13/Worker-Context-Protocol)
- WCP v1.0-rc1 spec (`spec/1.0-rc1.md`)
- WCP `did:wcp` method spec (`spec/did-method-wcp.md`)
- WCP RFCs 0001-0034 (`rfcs/`)

## 8. Authors

- [PRINCIPAL TO PROVIDE: primary author name, email, affiliation]
- [PRINCIPAL TO PROVIDE: additional authors if any]

## 9. Acknowledgments

- The Linux Foundation Projects LLC for ongoing dialogue on the donation trajectory.
- The W3C DID Working Group and Verifiable Credentials Working Group for the foundational specifications WCP builds on.
- The IETF SCITT Working Group for adjacent work on transparency services.
