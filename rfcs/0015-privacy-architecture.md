# RFC 0015: Privacy Architecture

- Author(s): Rentably (principal)
- Status: accepted (part of v1.0-rc1)
- Type: standards-track

## Summary

Adopts the privacy primitives in `spec/privacy-architecture.md`: PII field tagging in JSON Schemas, hash-only audit chain entries, tombstone pattern for erasure, alignment with PDPA/GDPR/CCPA.

## Design

See `spec/privacy-architecture.md`.

## Drawbacks

The tombstone pattern complicates audit chain verification slightly (verifiers must distinguish "tombstoned but valid chain" from "tampered chain"). The added discipline is justified by data-subject deletion compliance.

## Prior art

- GDPR Article 17 (right to erasure)
- Solid project's audit-trail-with-redaction approach
- Healthcare audit standards (HL7 ATNA) where tamper evidence and deletion compatibility coexist

## Implementation track

PII tagging in `spec/schemas/`; tombstone pattern implemented in the coordinator's audit chain module.
