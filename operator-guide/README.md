# WCP Operator Implementation Guide

**Status:** RECOMMENDED practice, not normative. Conformance does not require adoption of any practice in this guide.

The Worker Context Protocol (`spec/`) defines what the wire looks like. This guide covers what marketplace operators do **around** the protocol: reputation cold-start, dispute resolution, insurance, fraud detection, regulatory compliance, pricing.

The boundary is intentional. A protocol that tells operators how to run their marketplaces is a SaaS product with a JSON envelope, not a protocol. WCP defines primitives; operators define policies.

## Documents

- `onboarding.md`: worker and operator onboarding workflows
- `reputation-cold-start.md`: bootstrapping reputation for new workers (KYC prior, sponsor model, cold-start work pool patterns)
- `dispute-resolution.md`: escalation ladders, arbitrator selection, jurisdiction handling
- `insurance-partnerships.md`: insurance-product integration patterns
- `fraud-detection.md`: signals, telemetry, response patterns
- `regulatory-compliance.md`: jurisdiction-by-jurisdiction practical guidance
- `pricing-strategies.md`: marketplace pricing patterns

Each document offers patterns and examples. Operators choose what to adopt.
