# RFC 0017: Semantic Versioning Policy

- Author(s): Rentably (principal)
- Status: accepted (part of v0.2)
- Type: standards-track

## Summary

Adopts `spec/semver-policy.md`. MAJOR for breaking changes; MINOR additive; PATCH for clarifications. `schema_version` follows MAJOR.MINOR. Deprecation period at least 12 months.

## Drawbacks

A strict 12-month deprecation period slows evolution. The trade-off is implementer trust: protocols that break casually lose adopters.

## Prior art

- Semantic Versioning 2.0 (https://semver.org/)
- Kubernetes API versioning policy
- OpenAPI versioning conventions

## Implementation track

`CHANGELOG.md` at the repo root records each version's changes per category (breaking, additive, fix). Conformance suite versioning mirrors spec versioning.
