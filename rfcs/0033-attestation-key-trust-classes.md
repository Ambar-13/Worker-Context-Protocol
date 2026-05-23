# RFC 0033: Attestation Key Trust Classes

- Author(s): WCP TSC
- Status: open (v1.1 candidate)
- Type: standards-track
- Created: 2026-05-23
- Targets: v1.1

## Summary

Specifies an OPTIONAL `trust_class` field on each `attestation_keys[]` entry in a CapabilityDescriptor, plus an OPTIONAL `minimum_trust_class` field on `TaskDescriptor.attestation_requirement`. Lets operators in regulated, safety-critical, or high-value contexts gate task posting on hardware-rooted attestation guarantees without breaking compatibility for the software-keypair default.

## Motivation

A worker's attestation key signs every event it submits. v0.2 treats all keys as equivalent: a software keypair on a laptop signs as authoritatively as a TPM-attested key on an industrial controller. This is fine for the median case but breaks three specific deployments:

1. **Industrial robotics with safety-critical attestation.** A pharmaceutical-manufacturing operator requires that every robot dispatching a sterile-fill task signs with a hardware-attested key whose attestation envelope traces to the TPM 2.0 manufacturer.
2. **Healthcare logistics with regulated chain-of-custody.** Specimen-transport tasks under HIPAA-equivalent regimes (HITRUST, GDPR Article 32) require that the courier's signing key is at minimum hardware-attested via WebAuthn on the carrying device.
3. **Defense and infrastructure inspection.** Critical-infrastructure operators (national grid SCADA, port authority bridge cameras) cannot accept software keypair signatures for evidence used in audit-trail-of-record contexts.

Today these operators run private operator-side enforcement, refusing tasks/claim from low-trust workers via opaque policy. RFC 0033 makes the gate explicit, declared in the task descriptor, and verifiable.

## Design

### CapabilityDescriptor.attestation_keys entry extension

Each entry in `CapabilityDescriptor.attestation_keys[]` MAY include a new optional `trust_class` field:

```json
{
  "key_id": "primary",
  "did": "did:wcp:z...",
  "public_key_multibase": "z...",
  "algorithm": "Ed25519",
  "trust_class": "hardware-attested-tpm2"
}
```

If absent, the verifier MUST treat the entry as `software-keypair`.

### Initial trust class enum

| Value | Meaning |
|---|---|
| `software-keypair` | Default. Software-isolated key with no hardware backing claim. |
| `hardware-attested-tpm2` | TPM 2.0 attestation per TCG specifications. Remote-attestation evidence required at registration. |
| `hardware-attested-webauthn` | FIDO2/WebAuthn authenticator with attestation. Covers human-worker PWA on supporting devices, hardware security keys, platform authenticators. |
| `hardware-attested-secure-enclave` | Apple Secure Enclave, Android StrongBox, Pixel Titan M, equivalent. Vendor-specific attestation envelopes. |
| `hardware-attested-tee` | ARM TrustZone, Intel SGX, AMD SEV, equivalent. Common for industrial controllers and AMRs. |
| `delegated` | Key held by a trusted delegate; the delegation chain itself is the attestation. |

Future RFCs MAY register additional values via the standard process.

### TaskDescriptor.attestation_requirement extension

`TaskDescriptor.attestation_requirement` MAY include a new optional `minimum_trust_class` field:

```json
{
  "modes": ["sensor-witness", "owner-sign-off"],
  "threshold": "M-of-N",
  "M": 2,
  "N": 2,
  "evidence_schema": [...],
  "override_authority": "did:wcp:z...",
  "override_audit_required": true,
  "minimum_trust_class": "hardware-attested-tpm2"
}
```

If absent, the coordinator MUST treat the requirement as `software-keypair` (any key accepted).

### Verifier behavior

When a worker invokes `tasks/claim`:

1. Coordinator looks up the worker's current `attestation_keys[]`.
2. For each key the worker would use to sign attestations on this task, the coordinator checks `trust_class >= minimum_trust_class` per the ordering below.
3. If any required-mode key fails the check, coordinator rejects with `INSUFFICIENT_TRUST_CLASS` (new error code, range to be allocated).

### Trust class partial ordering

Hardware-attested classes are partially ordered. v1.1 declares:

```
software-keypair < {hardware-attested-tpm2, hardware-attested-webauthn,
                    hardware-attested-secure-enclave, hardware-attested-tee}
                < delegated
```

Note: `delegated` is "above" software-keypair only when the delegation chain itself terminates at a hardware-attested root. v1.1 leaves the chain-validation algorithm to operator policy; v1.2 RFC will normalize.

Within hardware-attested, no further ordering: a TaskDescriptor that demands `hardware-attested-tpm2` SHOULD also accept other hardware-attested classes unless the operator declares the requirement strictly. v1.1 adds an OPTIONAL `minimum_trust_class_strict: true` flag for the strict case.

### Verification at registration time

v1.1 does NOT mandate registration-time attestation verification (the out-of-band attestation envelope flow). Operators who require attestation-time verification SHOULD use evidence kinds from RFC 0034 (External Trust-Root Signed Evidence) to bind attestation envelopes into the audit chain at registration.

Open question on hardening: should v1.2 mandate registration-time attestation envelope verification for `hardware-attested-*` classes? Recommendation: no, because operator deployments vary widely; but operators MAY require it via policy and reject capabilities lacking attested registration.

### Reputation impact

Trust class is durable on the worker DID. Downgrading is allowed (e.g., key rotation from `hardware-attested-tpm2` to `software-keypair` when the TPM fails) but creates a reputation event tagged `wcp.reputation.trust_class_downgrade`. The reputation summary returned by the federation reputation-portability path (spec/federation.md) MUST include both the current trust class and the count of historical downgrades.

### Migration

- v0.2 capabilities have no `trust_class` field. v1.1 verifiers treat them as `software-keypair`.
- v1.1 capabilities MAY declare any trust class.
- v1.1 task descriptors with `minimum_trust_class` reject v0.2 workers if the requirement is above `software-keypair`.
- No v1.2 default flip; trust class remains opt-in by operator policy.

## Drawbacks

- Operator coordination cost: high-trust operators must publish their trust-class requirements in advance for workers to know what to deploy with.
- Worker fleet onboarding cost: workers must provision hardware-attested keys to qualify for hardware-attested tasks. This is one-time per worker but real.
- Attestation envelope diversity: TPM 2.0, WebAuthn, Apple SEP, Android StrongBox, ARM TrustZone, Intel SGX, AMD SEV all have different envelope formats. Verifiers must support all the classes the coordinator accepts. RFC 0034 helps by mapping each envelope format to a standardized evidence-kind handler.

## Alternatives

1. **Operator-only policy, no spec change.** Each operator enforces its own trust gate; tasks specify trust requirements opaquely. Loses interoperability across federated coordinators and forces every implementer to roll their own gate. Rejected.
2. **Mandatory trust classes on all keys.** Every key MUST declare a trust class explicitly. Breaks backward compat with v0.2. Rejected.
3. **Boolean hardware_attested flag instead of enum.** Loses the granularity needed to distinguish TPM from WebAuthn from delegated. Operators in mixed fleets (some industrial controllers with TEE, some human workers with WebAuthn) need the distinction. Rejected.

## Prior art

- WebAuthn attestation conveyance preferences (https://www.w3.org/TR/webauthn-2/#sctn-attestation) [VERIFIED]
- TCG TPM 2.0 Library Specification (https://trustedcomputinggroup.org/resource/tpm-library-specification/) [VERIFIED]
- TLS client certificate trust hierarchies [VERIFIED]
- IETF RATS (Remote Attestation Procedures) working group output [VERIFIED, https://datatracker.ietf.org/wg/rats/]

## Unresolved questions

1. **Should `delegated` trust class require a typed delegation-chain document?** Recommendation: yes, in v1.2, via a new evidence kind `delegation-chain` per RFC 0034.
2. **Should `hardware-attested-*` classes mandate registration-time attestation envelope verification?** v1.1 leaves to operator policy; v1.2 RFC may normalize.
3. **Should `minimum_trust_class_strict: true` flag exclude `delegated`?** Recommendation: yes; strict mode means hardware-only.
4. **Cross-coordinator trust class portability.** When a worker registered on Coordinator A with `hardware-attested-tpm2` is discovered by Coordinator B via federation, does B trust A's trust-class declaration? Recommendation: yes, when the federation trust anchor explicitly extends to trust-class declarations; otherwise B independently re-attests.

## Implementation track

v1.1 reference coordinator:
- New optional fields in `wcp_coordinator/schemas/capability_descriptor.json` and `task_descriptor.json`
- `wcp_coordinator/verifiers/trust_class.py` enforces the gate at `tasks/claim`
- New error code: `INSUFFICIENT_TRUST_CLASS` (range to be allocated in spec/error-codes.md update)

v1.1 SDK changes:
- `WorkerIdentity.set_trust_class(c: TrustClass)` (Python, TypeScript, Rust, Go)
- `Task.require_trust_class(c: TrustClass, strict: bool = False)` builder method

v1.1 conformance test cases (proposed; see `conformance/test-suite/level2.json` after RFC 0033 acceptance):
- L2.trust_class.software_default: capability without trust_class treated as software-keypair
- L2.trust_class.hw_attested_accept: capability with hardware-attested-tpm2 accepts task with same minimum
- L2.trust_class.hw_attested_reject: capability with software-keypair rejected for task minimum hardware-attested-*
- L2.trust_class.delegated_accept: delegated capability accepts task with minimum software-keypair
- L2.trust_class.strict_excludes_delegated: capability delegated rejected for task minimum hardware-attested-* strict
- L2.trust_class.downgrade_recorded: rotating from hardware-attested to software-keypair emits reputation downgrade event
