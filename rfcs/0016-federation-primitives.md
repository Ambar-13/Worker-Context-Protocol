# RFC 0016: Federation Primitives

- Author(s): Rentably (principal)
- Status: accepted (part of v0.2); amended at v0.955 (the `cross_coordinator_settlement` trust class is removed; federation rides on eight RPCs after v0.955).
- Type: standards-track

## Summary

Adopts the federation primitives in `spec/federation.md`: trust anchors, three trust classes after the v0.955 amendment (capability_discovery, reputation_query, audit_chain_export), and the rule that federation rides on the existing eight RPCs.

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

Federation endpoints documented in `federation.md`. The reference coordinator's federation implementation lands at v0.2 final; v0.2 ships the schema and contract.
