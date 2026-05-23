# RFC 0016: Federation Primitives

- Author(s): Rentably (principal)
- Status: accepted (part of v1.0-rc1)
- Type: standards-track

## Summary

Adopts the federation primitives in `spec/federation.md`: trust anchors, the four trust classes (capability_discovery, reputation_query, audit_chain_export, cross_coordinator_settlement), and the rule that federation rides on the existing nine RPCs.

## Design

See `spec/federation.md`.

## Drawbacks

Bilateral trust-anchor exchange does not scale linearly. RFC 0022 explores discovery mechanisms that avoid O(N^2) negotiations.

## Prior art

- ActivityPub / Fediverse: bilateral but with shared protocol
- Email federation (SMTP)
- Matrix federation
- The bilateral trust model of TLS certificate authorities (though WCP's federation does not have a global CA)

## Implementation track

Federation endpoints documented in `federation.md`. The reference coordinator's federation implementation lands at v1.0-rc1 final; v1.0-rc1 ships the schema and contract.
