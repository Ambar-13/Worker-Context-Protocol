# RFC 0034: External Trust-Root Signed Evidence

- Author(s): WCP TSC
- Status: open (v1.1 candidate)
- Type: standards-track
- Created: 2026-05-23
- Targets: v1.1

## Summary

Specifies the pattern by which evidence signed against an external trust root (an X.509 chain, a JWKS endpoint, or a non-`did:wcp` DID) is registered as a typed evidence kind and verified directly by the coordinator. Eliminates the "trust-shift-to-bridge" tax that currently forces vendor-rooted, OEM-rooted, government-rooted, or institution-rooted evidence to be re-signed by a `did:wcp` key before entering the audit chain. The verifier learns the external trust root explicitly, fetches its current keys per a freshness spec, and verifies signatures natively.

## Motivation

A growing class of WCP task attestations naturally carry external signatures:

- **Vendor-signed mission artifacts** from major robot platforms (Boston Dynamics Spot mission logs, ANYbotics mission summaries, Universal Robots UR-Sim certified runs)
- **Vehicle OEM telematics** signed by the manufacturer's TPM-rooted CA chain
- **Government-signed evidence** for regulated robots (FAA Part 107 drone-flight logs signed by the FAA-issued operator credential, MARAD-signed maritime vessel telemetry)
- **Instrument-vendor-signed scientific measurements** from precision instruments (Agilent, Thermo Fisher, Mettler Toledo, Keysight) where the audit-trail-of-record requirement demands the instrument's own signature
- **Hospital-system-signed medical chain-of-custody** signed by an institutional EHR system's key against the institution's PKI

Today, the only way to put this evidence in a WCP audit chain is to bridge it: a trusted operator or worker re-signs the external evidence with a `did:wcp` key. This is a trust-shift. The integrity claim now flows through the bridge's `did:wcp` key, not the original signer's key. A regulator examining the audit chain sees a `did:wcp` signature, not the vendor's or government's signature, and must trust the bridge transitively. For high-assurance contexts (regulated healthcare, defense, civil aviation) this is unacceptable.

RFC 0034 removes the bridge tax. The coordinator's evidence-kind verifier learns the external trust root, fetches its keys, and verifies natively. The audit chain entry records the original signature against the original trust root; auditors verify directly.

## Design

### New evidence kind family

A new family of evidence kinds is registered: `external-trust-root.<root-identifier>` where `<root-identifier>` is a registered string identifying the trust root.

Examples:
- `external-trust-root.faa-part107-operator`
- `external-trust-root.boston-dynamics-spot-mission`
- `external-trust-root.universal-robots-ur-sim`
- `external-trust-root.thermo-fisher-precision-instrument`
- `external-trust-root.epic-ehr-institution-pki`

Each registered entry declares:

```json
{
  "kind": "external-trust-root.<root-identifier>",
  "trust_anchor": {
    "type": "jwks-url | x509-chain | did-resolution",
    "location": "https://trust-anchor.example.org/.well-known/jwks.json",
    "freshness": {
      "max_age_seconds": 86400,
      "refresh_strategy": "polling | webhook | on-verify"
    },
    "cache_location_hint": "operator-side cache; coordinator MAY fetch per request or cache per max_age"
  },
  "verification": {
    "signature_algorithm": "RS256 | ES256 | EdDSA | <other>",
    "payload_schema": "URL to JSON Schema for the signed payload",
    "freshness_field": "issued_at",
    "max_payload_age_seconds": 3600
  },
  "wcp_field_mapping": {
    "audit_chain.evidence_payload": "external_payload.full_payload_hash",
    "audit_chain.collected_at": "external_payload.issued_at",
    "audit_chain.signer_identifier": "external_payload.kid",
    "audit_chain.signer_trust_anchor_ref": "trust_anchor.location"
  }
}
```

### Verification flow

1. Worker collects external-trust-root evidence (e.g., the vendor's signed mission log).
2. Worker emits the evidence via `tasks/attest` with `kind: "external-trust-root.<root-identifier>"` and the full signed payload in `evidence_payload`.
3. Coordinator's evidence kind verifier:
   - Looks up the registered entry for `<root-identifier>` (from this RFC's spec or the evidence kinds registry).
   - Fetches the trust anchor's keys per the freshness spec (cached if within `max_age_seconds`).
   - Verifies the signature using the declared algorithm against the trust anchor.
   - Validates payload schema and freshness (`issued_at` within `max_payload_age_seconds`).
   - Projects fields per `wcp_field_mapping` into the WCP audit chain entry.
4. Coordinator records the audit chain entry with:
   - `signer_identifier`: the external signer (e.g., FAA operator credential ID, instrument serial)
   - `signer_trust_anchor_ref`: the trust anchor URL or DID
   - `evidence_kind`: `external-trust-root.<root-identifier>`
5. Downstream auditors verify by fetching the trust anchor and re-validating; no `did:wcp` bridge in the trust chain.

### Registry process

New external-trust-root entries are proposed via the standard RFC process. Each RFC for a new family member MUST include:

- `<root-identifier>` (registered string)
- Trust anchor location (JWKS URL, X.509 chain or trust-store reference, or DID resolution)
- Verification logic (signature algorithm, payload schema URL or inline JSON Schema, freshness rules)
- WCP-side field mapping (how external evidence fields project into audit chain fields)
- Example evidence payload
- Operator deployment notes (caching, network policy, fallback if trust anchor is unreachable)

The registry lives in `rfcs/0003-evidence-kinds-registry.md` under a new subsection `external-trust-root.*`. RFC 0003 is updated to reference this RFC.

### Revocation handling

When an external trust root revokes a key (e.g., FAA revokes an operator's credential, an EHR institution decommissions a signing key):

**Option A (durable):** Audit chain entries accepted BEFORE the revocation remain valid; the audit chain records the acceptance time. Revocation affects only NEW evidence after the revocation timestamp.

**Option B (retroactive):** Audit chain entries verifiable against the revoked key are marked with a follow-on revocation entry. Re-verification flags them. Downstream consumers (dispute resolution, regulatory audit) decide whether to honor.

**Recommendation:** Option A. The audit chain is forensic record; tampering with past entries violates the integrity guarantee. Revocation is durable going forward only. Coordinators MAY emit a `wcp.revocation.external-trust-root` audit chain entry referencing the revoked key and the timestamp, providing forensic visibility without retroactive invalidation.

### Interaction with trust class (RFC 0033)

External-trust-root evidence interacts with the worker's declared `trust_class`. The signing root is the external trust root; the worker's `trust_class` declaration is about the worker's `did:wcp` key. These are orthogonal:

- A worker with `software-keypair` `trust_class` MAY emit `external-trust-root.*` evidence; the external trust root's authority is independent.
- A task's `minimum_trust_class` constraint is checked against the worker's `did:wcp` key, NOT the external trust root.
- Operators wanting to mandate external-trust-root evidence for a task MUST do so via the `attestation_requirement.evidence_schema` (require the specific `external-trust-root.<root-identifier>` kind), not via `minimum_trust_class`.

### Migration

v1.0-rc1 has no concept of external trust roots. v1.1 adds the family; v1.0-rc1 verifiers reject `external-trust-root.*` evidence kinds with `UNKNOWN_EVIDENCE_KIND`. v1.1 verifiers handle the family natively.

Operators upgrading from a bridge-based workflow:

1. Catalog the external trust roots currently bridged via `did:wcp` re-signing.
2. Propose RFC additions for each (one RFC per root, or batched).
3. Update verifier configuration to point at the trust anchor locations.
4. Cease bridge re-signing for the catalogued roots; new evidence flows through native verification.
5. Existing audit chain entries that were bridged remain valid under the bridge's signature; new entries flow natively.

## Drawbacks

- Operator-side complexity: each external trust root requires its own trust anchor fetching, caching, and freshness policy. Per-operator deployment cost.
- Network policy: coordinators must be able to reach trust anchor locations; air-gapped deployments must pre-fetch and cache.
- Cache invalidation: a trust anchor's key rotation may not propagate to all coordinators simultaneously. Operators must accept a brief window where different coordinators verify against different key sets.
- Registry growth: as more trust roots are added, the registry expands. Discoverability and tooling support are operator concerns.

## Alternatives

1. **Status quo (bridge re-signing).** Forces every external signature through a `did:wcp` re-sign. Loses the original signer's authority; trust-shifts to the bridge. Rejected; this is the problem RFC 0034 solves.
2. **Inline trust anchor in every evidence payload.** Each evidence payload includes its trust anchor's full key material. Bloats audit chain entries; loses caching benefits; key updates require re-signing. Rejected.
3. **Generic JWS/JWE verifier without registration.** Accept any JWS-shaped evidence and verify against the embedded `kid`. Loses the protocol-side registration of which roots are acceptable; opens DoS vector (verify against attacker-controlled keys); breaks operator policy enforcement. Rejected.
4. **Per-operator policy without spec change.** Operators each implement their own external-trust-root verifier. No interop; auditors examining audit chain entries cannot independently verify without operator-specific knowledge. Rejected.

## Prior art

- JOSE (JSON Object Signing and Encryption) JWS family of RFCs (RFC 7515, 7517, 7518) [VERIFIED]: defines JWKS, JWS, signature algorithms. RFC 0034 builds on JOSE for the JWKS trust-anchor case.
- X.509 PKI trust hierarchies [VERIFIED]: standard for chain-of-trust verification.
- WebAuthn attestation conveyance preferences [VERIFIED]: similar pattern for hardware-attested credentials.
- IETF SCITT (Supply Chain Integrity, Transparency, and Trust) working group [VERIFIED, https://datatracker.ietf.org/wg/scitt/]: closely related work for software supply chain. WCP-Lite's audit chain and SCITT's transparency service are structurally analogous.
- Sigstore's Rekor transparency log and Fulcio CA [VERIFIED, https://www.sigstore.dev/]: similar pattern of binding external identity to a verifiable trust root for evidence.

## Unresolved questions

1. **Revocation handling.** Option A (durable) recommended; community discussion welcome on whether high-assurance contexts (medical chain-of-custody) require retroactive marking.

2. **Trust anchor unreachability.** What happens when a coordinator cannot fetch the trust anchor (network outage, DNS failure, anchor host decommissioned)? Recommendation: reject the evidence with `TRUST_ANCHOR_UNREACHABLE`; operators MUST configure fallback caching for known-good keys.

3. **Cross-coordinator trust anchor sharing in federation.** When Coordinator B receives a federated task whose external-trust-root evidence requires a trust anchor only Coordinator A has cached, can B verify via A as a proxy? Recommendation: no; each coordinator MUST independently verify against the trust anchor location. Caching is operator-side.

4. **Trust anchor diversity in regulated environments.** Some regulators require the trust anchor be hosted by the regulator's own infrastructure (FAA hosts the FAA operator credential anchor; FDA hosts the FDA hospital signing anchor). v1.1 spec mandates that operators MUST be able to point at any HTTPS-accessible JWKS URL or X.509 chain; specific anchor hosting requirements are operator-policy.

5. **Time-synchronization of trust anchor data.** Trust anchor freshness uses the coordinator's clock. Drift across federation peers (per RFC 0032 time-sync drift bound) may cause divergent verification outcomes. Recommendation: federation trust anchors declare a primary time source for trust anchor freshness; both coordinators sync to it.

## Implementation track

v1.1 reference coordinator:
- `wcp_coordinator/verifiers/external_trust_root.py`: pluggable verifier framework with per-trust-anchor handlers
- Cache layer with operator-configurable TTL
- Updates to `audit_chain.py` to record the `signer_trust_anchor_ref` and `signer_identifier` fields

v1.1 evidence kinds registry update:
- One-line addition to `rfcs/0003-evidence-kinds-registry.md` noting that the `external-trust-root.*` family is registered via RFC 0034. (See cross-reference below.)

v1.1 conformance test cases (proposed; see `conformance/test-suite/level2.json` after RFC 0034 acceptance):
- L2.external_trust_root.jwks_verify_success: evidence signed by a JWKS-anchored key verifies
- L2.external_trust_root.signature_mismatch_reject: evidence with mismatched signature rejected
- L2.external_trust_root.payload_freshness_reject: evidence with `issued_at` older than `max_payload_age_seconds` rejected
- L2.external_trust_root.trust_anchor_unreachable_reject: coordinator that cannot fetch trust anchor rejects evidence
- L2.external_trust_root.audit_chain_records_signer: audit chain entry records `signer_identifier` and `signer_trust_anchor_ref` correctly

## Cross-references

- This RFC defines the `external-trust-root.*` family registered in `rfcs/0003-evidence-kinds-registry.md`.
- RFC 0003 (Evidence Kinds Registry) is updated to add a subsection acknowledging the family is governed by this RFC.
- RFC 0033 (Attestation Key Trust Classes) is orthogonal; see "Interaction with trust class" above.
