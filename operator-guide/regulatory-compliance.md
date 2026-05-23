# Operator Guide: Regulatory Compliance

**Status:** RECOMMENDED practice; not normative. Jurisdictional law evolves; verify current requirements with local counsel.

WCP is jurisdiction-neutral. The protocol provides primitives (signed evidence, hash-linked audit chain, typed PII fields) that support compliance; the legal compliance posture belongs to the operator.

## 1. Singapore

### PDPA (Personal Data Protection Act 2012)

Personal data protection law administered by the PDPC. Operator-side responsibilities:

- Consent for collection, use, disclosure of personal data.
- Purpose limitation.
- Notification of significant data breaches.
- Data Protection Officer registration.
- Right of access; right of correction; right of withdrawal of consent.

WCP supports:

- PII tagging in JSON Schemas (`spec/privacy-architecture.md` Section 1).
- Hash-only audit chain entries (Section 2 of the same doc).
- Tombstone pattern for erasure (Section 3).

### MOM and Workplace Safety and Health Act

Worker safety and labor regulations administered by the Ministry of Manpower. Applies to:

- Employee classification (employee vs independent contractor; the platform-worker question).
- Workplace safety for site-based work.
- Foreign worker permits (if applicable).

WCP-side considerations: the platform classification depends on the operator's relationship with workers; the protocol is neutral. Audit chain MAY be used as evidence in MOM inquiries about completed work.

### IMDA

Telecommunications and content regulation. Relevant to:

- Cybersecurity of the coordinator.
- TLS posture (`spec/security-baseline.md`).
- WebRTC streaming for supervision (compliance with content standards).

### CAAS

Civil Aviation Authority of Singapore. Relevant only if WCP is used to dispatch drone-based work (`observe_and_report` with `class: autonomous_robot, kinematics: aerial`).

## 2. European Union

### GDPR

WCP supports the GDPR rights via the privacy architecture document. Operators MUST:

- Have a lawful basis for processing (consent, contract, legitimate interest, ...).
- Appoint a DPO if processing crosses thresholds.
- Honor data subject rights via the tombstone pattern.
- Comply with cross-border transfer rules (Standard Contractual Clauses for non-adequate jurisdictions).

For federated tasks (`spec/federation.md`), the operator MAY refuse federation with peers in non-compliant jurisdictions (`FEDERATION_JURISDICTION_REFUSED`, error code -50006).

### EU AI Act

Risk-based regulation of AI systems. The Act categorizes AI systems by risk; WCP-driven systems where an AI agent autonomously dispatches physical work may fall under "high-risk" if the work touches health, safety, or fundamental rights.

Operator responsibilities: conformity assessment; transparency obligations; logging requirements that WCP's audit chain partially satisfies.

### Directive on platform work (proposed; status varies)

Several EU member states have or are developing platform-work regulations affecting worker classification. WCP does not bind classification; operators should verify per-state requirements.

## 3. United States

### CCPA / CPRA (California)

Similar privacy framework to GDPR; data subject rights, with the addition of opt-out of sale rights. WCP's tombstone and PII tagging support.

### State-by-state contractor classification

Worker classification rules vary by state (California's ABC test, Massachusetts's similar tests, vs more flexible tests elsewhere). Federally, the FLSA standard applies. The protocol does not classify; the operator does.

### HIPAA

Out of scope at v0.2 (medical task class is refused; `spec/0.2.md` Section 10).

## 4. Other jurisdictions

| Jurisdiction | Privacy law | Notes |
|---|---|---|
| United Kingdom | UK GDPR | Mirrors EU GDPR post-Brexit |
| Brazil | LGPD | Similar framework to GDPR |
| Canada | PIPEDA, provincial laws | Federal + provincial layer |
| Japan | APPI | Notification-based |
| Australia | Privacy Act | OAIC-administered |
| India | DPDPA 2023 | Recent enactment; rules evolving |

Operators serving these jurisdictions should engage local counsel.

## 5. Tax considerations

- VAT/GST on platform fees: per jurisdiction.
- Withholding for foreign workers: per jurisdiction.
- Worker income reporting: typically operator-side (Form 1099 in the US; CPF reports in Singapore; etc.).

WCP does not address tax; the operator's accounting integrates with `tasks/settle`.

## 6. Audit cooperation

A typical regulator request:

> Show me the audit trail for tasks completed in (jurisdiction) between (date range).

The WCP coordinator's audit chain export (`wcp-audit/1.0-rc1` format) covers this. Operators publish how to make a request; standard SLA is 30 days.

## 7. What WCP does NOT do

- Make any operator compliant by default. Compliance is a posture, not a protocol artifact.
- Replace legal counsel.
- Substitute for jurisdictional-specific operator workflows (e.g., breach notification timelines vary by jurisdiction).

The protocol's contribution is to make the operator's compliance posture cheaper to construct by providing tamper-evident evidence and structured PII handling.
