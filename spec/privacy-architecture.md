# WCP Privacy Architecture

**Companion to:** spec/1.0-rc1.md
**Status:** normative
**Compiled:** 2026-05-23

WCP MUST be implementable in jurisdictions with strict personal-data-protection regimes: PDPA (Singapore), GDPR (EU), CCPA (California), and analogous frameworks. This document defines the privacy primitives the protocol exposes and the operator-side responsibilities the protocol does not assume.

## 1. PII field tagging

Typed objects MAY mark fields as `wcp:pii` via the JSON Schema annotation:

```json
{
  "type": "object",
  "properties": {
    "customer_phone": {
      "type": "string",
      "wcp:pii": "phone_number",
      "wcp:redactable": true
    }
  }
}
```

Values of `wcp:pii`: `email`, `phone_number`, `name`, `address`, `geolocation_fine`, `biometric`, `financial`, `health`, `id_document`, `other`.

A conformant implementation MUST honor `wcp:redactable: true` when producing the operator's audit-trail export.

## 2. Hash-only audit chain entries

By default, the audit chain stores `payload_hash` per entry, not the full payload. Operators MAY store the full payload alongside in a separate PDPA/GDPR-compatible retention store. The audit chain's tamper evidence is preserved with hash-only entries; the operator can prove "this hash was logged at this time" without retaining the underlying payload past its lawful retention window.

The schema in `spec/schemas/audit-chain-entry.json` requires `payload_hash` and makes `payload` optional. Operators choose retention policy per jurisdiction.

## 3. Deletion-compatible primitives via tombstone pattern

GDPR's right to erasure and CCPA's deletion right require operators to delete personal data on request. The audit chain is append-only, so deletion is done by **tombstoning**:

```
Original entry:
  payload: { "customer_phone": "+65********", ... }
  payload_hash: <h1>

Tombstone entry (appended after deletion):
  event_type: "pii_tombstoned"
  payload: { "tombstoned_entries": [<entry_id>], "tombstone_reason": "data subject deletion request" }
  prev_hash: <chain head at time of tombstone>
  this_hash: <h2>

After tombstoning, operator deletes `payload` from the tombstoned entries (sets to null in the
underlying store) while preserving `payload_hash`. The chain remains verifiable: every link still
hashes correctly because the chain hash includes `payload_hash`, not the raw payload.
```

Tombstones are themselves signed audit entries. A data subject may request a copy of the tombstone receipt as proof of erasure.

## 4. PDPA / GDPR / CCPA alignment

| Right | WCP support |
|---|---|
| Right to access | Operator queries the audit chain for entries by the data subject's DID or by their PII fields (joined via the operator-side retention store) |
| Right to rectification | Operator appends a corrective audit chain entry; original entries remain tombstoned but the corrected entry supersedes for downstream consumers |
| Right to erasure | Tombstone pattern in Section 3 |
| Right to data portability | Audit chain export in `wcp-audit/1.0-rc1` JSON format includes all entries with their full payloads (where retained); see `wcp_coordinator/audit_chain.py` for the export format |
| Right to object | Operator-side; not WCP-normative |
| Right to be informed | Operator-side privacy policy; not WCP-normative |
| Data minimization | Evidence payloads MUST NOT include raw sensor data (e.g., photos, recordings) beyond what is required by the kind; only hashes are normative |
| Purpose limitation | Operator-side; not WCP-normative |

## 5. Cross-border data flow

WCP is jurisdiction-neutral. Operators in cross-border deployments MUST:

- Honor data-localization requirements (e.g., PDPA cross-border transfer notice; GDPR Standard Contractual Clauses for non-adequate jurisdictions).
- Tag the coordinator's primary jurisdiction in its `did:wcp` document `service` array under `wcp:metadata.primary_jurisdiction`.
- Refuse federation peer requests that would route PII into a non-compliant jurisdiction; see `federation.md`.

## 6. Minor and special-category data

Tasks involving minors as subjects are out-of-scope at v1.0-rc1 per spec Section 10. Special-category data (health, biometric, financial, political opinion) is similarly out-of-scope for v1.0-rc1 reference coordinator deployments; operators MAY relax with explicit RFC clearance and signed operator policy. The PII tagging (Section 1) supports special-category labels (`biometric`, `health`) so future RFCs can add normative handling.

## 7. Consent and audit

Every state transition that touches PII MUST emit an audit chain entry with `actor_did` set to the party authorizing the transition (worker for their own signature; coordinator for system actions; operator-ops for overrides). This is the protocol's contribution to consent demonstrability; the legal basis for the underlying processing is operator-side.

## 8. Encryption baseline

- In transit: TLS 1.3, WSS only (see `security-baseline.md`).
- At rest: operator responsibility; recommended AES-GCM 256 or equivalent.
- Key material (worker keypairs): TPM- or secure-element-backed where available; software-backed fallback acceptable with trust class declared in CapabilityDescriptor.

## 9. What WCP does NOT do for privacy

- Encrypt event payloads end-to-end between worker and agent (the coordinator is in the middle by design).
- Anonymize worker identity (the worker DID is pseudonymous, not anonymous; reputation portability requires DID stability).
- Provide differential privacy on aggregate queries (operator MAY layer this on the audit-chain export).
- Mandate any specific consent UI; the contractor PWA reference and the robot plugin reference each implement consent flows appropriate to their channel.
