---
title: "Worker Context Protocol"
abbrev: WCP
docname: draft-wcp-protocol-00
category: info
ipr: trust200902
area: Applications
workgroup: Independent submission
keyword: agent, worker, robotics, attestation, federation, did

author:
  -
    ins: "[PRINCIPAL TO PROVIDE: author initial last]"
    name: "[PRINCIPAL TO PROVIDE: author full name]"
    org: "[PRINCIPAL TO PROVIDE: author organization]"
    email: "[PRINCIPAL TO PROVIDE: author email]"

normative:
  RFC2119:
  RFC8174:
  RFC8032:  # Ed25519
  RFC7515:  # JOSE JWS
  RFC7517:  # JWK
  RFC8785:  # JSON Canonicalization

informative:
  W3C-DID-CORE:
    target: https://www.w3.org/TR/did-core/
    title: Decentralized Identifiers (DIDs) v1.0
  MCP:
    target: https://modelcontextprotocol.io/
    title: Model Context Protocol

--- abstract

The Worker Context Protocol (WCP) is an open protocol that coordinates
AI agents and physical-world workers (humans, autonomous robots,
teleoperated systems, and hybrid worker classes) through one RPC
surface. The protocol is structured as JSON-RPC 2.0 over WebSocket
with a typed object model (CapabilityDescriptor, TaskDescriptor,
AttestationEvidence), a did:wcp identity method built on W3C DID
Core, a hash-linked audit chain, a two-phase escrow settlement
primitive, and a federation layer allowing independent coordinators
to peer. This document describes the protocol, its identity model,
its attestation and settlement primitives, and its federation
mechanism. It is submitted as an individual contribution for community
discussion and potential working group adoption.

--- middle

# Introduction

This document describes the Worker Context Protocol (WCP), an open
protocol for coordinating AI agents and physical-world workers across
institutional and industrial domains. WCP is to physical-world work
what the Model Context Protocol (MCP) is to software tools: same
algorithmic lever (in-band capability discovery plus a typed call
contract), applied to a different domain. The primitives MCP does
not need because tools cannot fail in physically irreversible ways
(typed attestation, supervision handoff, two-phase settlement,
partial-completion abort) are first-class in WCP.

WCP is structured around four design principles:

1. The protocol is vendor-neutral; specific operators, escrow
   providers, jurisdictions, and currencies are application-layer.
2. The protocol is worker-class-agnostic; the matching engine and
   the attestation verifier discriminate by structural properties,
   not by worker class.
3. The protocol uses W3C DID Core for identity; the did:wcp method
   is registered with the W3C DID method registry.
4. The protocol audit trail is hash-linked and signed; tampering
   is forensically detectable.

The current version is v1.0-rc3 (release candidate). v1.0 final
requires multiple independent implementations passing the conformance
suite at Level 2, at least one passing at Level 3, at least one
external paper accepted at a major venue, and a neutral steward
acceptance.

## Conventions and Definitions

{::boilerplate bcp14-tagged}

## Terminology

- Agent: an entity (typically AI-driven) that posts tasks.
- Worker: an entity that claims and executes tasks. May be a human,
  autonomous robot, teleoperated robot, semi-autonomous platform, or
  hybrid worker class.
- Coordinator: an entity (typically a server) that mediates between
  agents and workers; hosts the RPC surface, the audit chain, and
  the settlement primitive.
- Operator: the institutional entity running a coordinator.
- Federation: bilateral trust relationships between coordinators
  that allow capability discovery, task posting, and reputation
  portability across coordinator boundaries.

# Protocol Overview

WCP defines 9 RPC methods:

1. capabilities/list: worker -> coordinator capability publish
2. capabilities/subscribe: agent -> coordinator capability discovery
3. tasks/post: agent -> coordinator task submission with bonded escrow
4. tasks/claim: worker -> coordinator task acceptance with signature
5. tasks/execute: worker -> coordinator execution start
6. tasks/attest: worker -> coordinator evidence submission
7. tasks/settle: coordinator -> settlement layer payout
8. tasks/supervise: worker -> coordinator supervision handoff
9. tasks/abort: any party -> coordinator cancellation

All RPCs are JSON-RPC 2.0 over WebSocket. Long-lived sessions are
the norm; short-lived HTTPS-plus-webhook is supported for backends
that cannot hold connections.

# Identity Model

WCP identity uses the did:wcp method, registered with W3C. The
method specification is in spec/did-method-wcp.md of the reference
repository. Briefly:

- Identifier syntax: did:wcp:&lt;multibase-prefix&gt;&lt;encoded-key-bytes&gt;
- Default algorithm: Ed25519
- Default encoding: base58btc (multibase prefix 'z')
- Three roles: worker, operator, coordinator (federation peer)
- Resolution: bilateral between coordinators; no central registry

The v1.0-rc1 grammar uses raw base58 without a multibase prefix;
v1.1 adds the multibase prefix per WCP RFC 0031 with a three-version
compatibility window. v2.0 deprecates raw base58 acceptance.

# Attestation

Every WCP audit chain entry is signed. The signature semantics depend
on the attestation mode:

- sensor-witness: telemetry from a sensor (GPS, accelerometer,
  weight, photo with EXIF)
- third-party-witness: signature from a designated co-signer DID
- cryptographic-presence: ephemeral key proof of physical presence
- owner-sign-off: signature from the owner DID indicating completion

A TaskDescriptor declares its required attestation_requirement with
modes, threshold (any | all | M-of-N), evidence_schema (list of
required evidence kinds per mode), and an optional override_authority
DID.

WCP RFC 0033 (post-v1.0-rc1) extends the model with attestation key
trust classes (software-keypair, hardware-attested-tpm2,
hardware-attested-webauthn, etc.). WCP RFC 0034 (post-v1.0-rc1)
extends with external-trust-root signed evidence (X.509 chains,
JWKS endpoints, non-did:wcp DIDs).

# Settlement

WCP settlement is two-phase: hold-on-post, capture-on-attest. The
TaskDescriptor declares escrow_provider, currency, amount, and
split[] (list of recipient DIDs with percentages).

For tasks crossing federation boundaries (agent on Coordinator A,
worker on Coordinator B), WCP RFC 0032 (post-v1.0-rc1) extends with
cross-coordinator settlement clearing. Three models are analyzed
(A-side capture B-side payout reconciliation; A-side capture on-chain
transfer to B-side; shared escrow provider); the recommended v1.1
primitive is the second model with a new audit chain entry kind
federation-settlement-transfer.

# Federation

Federation is bilateral. Two coordinators that peer exchange a
signed trust anchor declaring the scope of trust (capability
discovery, task posting, reputation portability, audit-chain
export). Federation does not require a global trust anchor; each
coordinator decides which peers to trust.

The audit chain integrity guarantee extends across federation
boundaries: a federated audit chain export from Coordinator B can
be verified independently on Coordinator A by re-running the
hash-link computation.

# Audit Chain

Every state transition emits an audit chain entry. Each entry
includes:

- entry_id (UUID)
- previous_entry_hash
- entry_hash (SHA-256 over canonical-JSON-encoded entry contents)
- task_id, claim_id (as relevant)
- timestamp (RFC 3339)
- signer_did
- signature (JOSE JWS or detached signature)
- payload (mode-specific)

The hash-link structure provides tamper-evidence; modifying any
entry invalidates the chain from that entry forward.

# Security Considerations

WCP's threat model is documented in spec/threat-model.md of the
reference repository. Briefly:

- Private key theft (mitigations: trust class declaration per
  RFC 0033, hardware attestation envelopes)
- Replay attacks (mitigations: nonce in signed payloads, timestamp
  freshness)
- Federation poisoning (mitigations: signed trust anchors,
  bilateral verification)
- DDoS on coordinators (mitigations: standard rate-limiting at the
  WebSocket layer)
- Sybil identities (mitigations: attestation key trust classes;
  registration-time verification per operator policy)

# IANA Considerations

This document requests no IANA actions. Future work may register:

- did:wcp in the W3C DID method registry (via W3C, not IANA)
- WCP-specific media types if media-type registration is preferred
  for the JSON-RPC envelope

# References

## Normative References

- {{RFC2119}}
- {{RFC8174}}
- {{RFC8032}} Ed25519
- {{RFC7515}} JSON Web Signature (JWS)
- {{RFC7517}} JSON Web Key (JWK)
- {{RFC8785}} JSON Canonicalization Scheme

## Informative References

- W3C DID Core 1.0
- Model Context Protocol (MCP)
- W3C Verifiable Credentials Data Model 1.1
- IETF SCITT (Supply Chain Integrity, Transparency, and Trust) working group output
- VDA 5050 Open Source Reference Implementation
- WCP repository (https://github.com/Ambar-13/Worker-Context-Protocol)

## Acknowledgments

The W3C DID Working Group and Verifiable Credentials Working Group
for foundational specifications. The IETF SCITT working group for
adjacent work on transparency services. The Linux Foundation
Projects LLC for ongoing dialogue on the donation trajectory.

# Appendix A. Future Work

- Post-quantum signature algorithms (planned via WCP RFC 0031
  multibase migration)
- Selective disclosure (potential bridge from W3C Verifiable
  Credentials selective disclosure)
- Standardized federation discovery (no current spec; bilateral
  peering is the v1.0-rc1 norm)
- Coordinator failover and high availability semantics (not
  specified in v1.0-rc1; left to operator implementation)
