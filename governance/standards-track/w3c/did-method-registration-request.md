# DID Method Registration Request: did:wcp

**Per W3C DID Specification Registries (https://www.w3.org/TR/did-spec-registries/)**

**Method name:** wcp
**Method specification URL:** [PRINCIPAL TO PROVIDE: stable URL for spec/did-method-wcp.md, e.g., the GitHub pages URL or W3C-hosted location]
**Registration contact:** [PRINCIPAL TO PROVIDE: name, email]
**Registration date:** [PRINCIPAL TO PROVIDE: submission date]
**Status:** Provisional (pending W3C DID Working Group review)

---

## 1. Method name

`wcp`

## 2. Method-specific identifier syntax

Current (v0.2):

```
did:wcp:<base58btc-encoded-ed25519-public-key>
```

Future (v1.1, per WCP RFC 0031):

```
did:wcp:<multibase-prefix><base58btc-or-other-encoding>
```

Where multibase-prefix defaults to `z` (base58btc) per the multibase RFC draft. The v1.1 grammar accepts both forms during a three-version compatibility window; legacy raw-base58 identifiers (v0.2) remain valid through v2.0.

## 3. Method operations

`did:wcp` supports:

- **Create** (implicit): identifier is derived from the public key; no on-chain or registry operation needed.
- **Read (resolve)**: resolution is bilateral between WCP coordinators. Each coordinator maintains a resolver for its registered identities. Cross-coordinator resolution proceeds via federation (WCP RFC 0016).
- **Update**: rotating the signing key is allowed; the worker's reputation history binds to the DID, not the key. Key rotation produces a reputation event.
- **Deactivate**: per the method spec; a deactivation entry in the audit chain records the change.

## 4. Algorithms

Initial: Ed25519 (RFC 8032).

Future: post-quantum signature algorithms when standardized; the multibase grammar (RFC 0031) accommodates variable-length keys.

## 5. Cryptographic privacy considerations

- Workers' public keys are exposed in the audit chain to enable independent verification.
- Worker DIDs are linkable across tasks within a coordinator (this is intentional; reputation binds to the DID).
- Cross-coordinator linkability depends on federation peering; without a trust anchor between coordinators, a worker's identity on Coordinator A is unlinkable to its identity on Coordinator B even if it uses the same key (because resolution is bilateral).
- Selective disclosure: not directly supported in v0.2; a future RFC may bridge VC Selective Disclosure into WCP audit chain entries.

## 6. Method-specific extensions

- **Connectivity profile** (WCP RFC 0029): workers MAY declare intermittent connectivity in their CapabilityDescriptor.
- **Attestation key trust class** (WCP RFC 0033): workers MAY declare hardware-attestation classes on their `attestation_keys[]`.
- **External trust-root signed evidence** (WCP RFC 0034): the audit chain accepts evidence signed against external trust roots beyond `did:wcp`.

## 7. Compliance with DID Core

- `did:wcp` complies with W3C DID Core 1.0.
- All required DID Document properties (id, verificationMethod, authentication, assertionMethod) are supported.
- Resolution metadata MUST be returned per DID Core 5.2.
- DID Document representation: JSON-LD (the default) and JSON (per DID Core 6.3).

## 8. Test vectors

Reference implementations produce identical canonical DID strings from identical Ed25519 public keys. Test vectors are documented in `wcp_sdk_python/tests/test_identity_canonical_did.py` and across the four reference SDKs (Python, TypeScript, Rust, Go); the cross-SDK conformance test verifies this.

Example test vector (Ed25519 key bytes -> did:wcp):

```
Ed25519 public key bytes (hex): 3F D6 ... (32 bytes)
did:wcp v0.2: did:wcp:zA1B2... (raw base58)
did:wcp v1.1: did:wcp:zzA1B2... (multibase-prefixed; the leading 'z' is multibase, the rest is base58btc payload)
```

## 9. Security considerations

Threats and mitigations per `spec/threat-model.md` in the WCP repository:

- **Private key theft**: standard ed25519 protections; trust class (RFC 0033) lets operators require hardware-attested keys.
- **DID enumeration**: linkability within a coordinator is intentional; cross-coordinator linkability depends on federation peering.
- **Reputation gaming**: reputation events recorded in the audit chain are tamper-evident; key rotation does not reset reputation but creates a typed event.
- **Quantum threat**: Ed25519 is vulnerable to a sufficiently large quantum computer (Shor's algorithm). The v1.1 multibase migration (RFC 0031) lets WCP migrate to PQ algorithms without changing the method name.

## 10. Method spec stable URL

[PRINCIPAL TO PROVIDE: stable URL for the latest version of `spec/did-method-wcp.md`]

Mirrored at:
- [PRINCIPAL TO PROVIDE: any alternate mirrors, e.g., w3c-ccg drafts repository if accepted]
- https://github.com/Ambar-13/Worker-Context-Protocol/blob/main/spec/did-method-wcp.md

## 11. Method spec maintainers

- [PRINCIPAL TO PROVIDE: editor name, email]
- Post-LF acceptance: the LF-stewarded TSC inherits maintainer responsibility per `proposed-charter.md`.

## 12. Contact for the registry

- **Registration contact**: [PRINCIPAL TO PROVIDE: name, email]
- **Security disclosure**: per `SECURITY.md` in the WCP repository
- **General inquiries**: GitHub issues on the WCP repository
