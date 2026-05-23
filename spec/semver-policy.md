# WCP Semantic Versioning Policy

**Companion to:** spec/1.0-rc1.md
**Status:** normative
**Compiled:** 2026-05-23

WCP follows semantic versioning [verified, https://semver.org/] with the protocol-specific rules below.

## Version scheme

`MAJOR.MINOR.PATCH[-prerelease]`

- `MAJOR`: breaking changes. Bumped only on TSC-approved RFC.
- `MINOR`: additive changes; back-compatible. New RPCs are NOT minor (the surface is locked at v1.0); new evidence kinds, new descriptor types, new error codes in unused ranges, new optional fields ARE minor.
- `PATCH`: clarifications, typo fixes, examples; no schema or semantics change.
- `prerelease`: `rc1`, `rc2`, ... (release candidates) or `alpha.N`, `beta.N` (pre-rc work).

Current version at this writing: `1.0-rc1` (release candidate 1 of v1.0).

## `schema_version` on typed objects

Every typed object carries `schema_version`. The value is `wcp/MAJOR.MINOR` (PATCH is silent for payloads; the value does not change between PATCH releases). For prereleases, the value includes the prerelease tag: `wcp/1.0-rc1`.

A v1.0 implementation MUST accept payloads with `schema_version: wcp/1.0-rc1` for the duration of the deprecation overlap window (Section 5).

## What is breaking

The following are MAJOR changes:

- Removing or renaming an RPC method.
- Removing a required field from any typed object.
- Changing the type of an existing field.
- Changing the semantics of an existing field value.
- Changing the lifecycle state machine (adding states is breaking; the matrix expansion forces re-verification).
- Changing the audit chain hash algorithm or canonicalization.
- Changing the DID method spec in a way that invalidates existing DIDs.

## What is additive

The following are MINOR (back-compatible) changes:

- Adding a new evidence kind to RFC 0003.
- Adding a new optional field to a typed object.
- Adding a new error code in an unused range.
- Adding a new federation trust class.
- Adding a new descriptor_type (application-layer).
- Adding new entries to enums with `additionalValues: true` flagged.

## What is patch

- Documentation clarification.
- Example fixes.
- Spec text reformatting.
- Schema description string changes.

## Deprecation policy

A breaking change MUST be preceded by at least one MINOR release that introduces the replacement and marks the old form as deprecated. The deprecation period is **at least 12 months from the deprecated MINOR release to the MAJOR removal**.

Deprecation is signaled by:

1. The deprecated field's JSON Schema gains a `"deprecated": true` annotation per JSON Schema 2020-12 `format.json-schema`.
2. The spec section describing the field gains a "Deprecated in v1.X; removed in v2.0" header.
3. The CHANGELOG.md (root) records the deprecation with the planned removal version.
4. Implementations SHOULD emit a `wcp:deprecated_field` log entry when accepting a deprecated payload.

## Back-compat test fixtures

For every MAJOR transition, the conformance suite MUST include "compatibility tests" that verify the new implementation correctly accepts payloads carrying the deprecated form during the overlap window. These fixtures live in `conformance/fixtures/back-compat/MAJOR.MINOR/`.

## Conformance suite versioning

The conformance suite follows the same versioning. A passing report against suite version X.Y is valid for the deprecation overlap window of X.Y; once X.Y is removed, the implementation MUST re-run against the current suite.

## Prerelease quality bar

A prerelease (e.g., `rc1`) is not v1.0 final. Specifically:

- **Adoption validation has not occurred.** RC labels are author commitments to a candidate surface; v1.0 final requires multiple independent implementations passing the conformance suite at Level 2 and at least one passing at Level 3.
- **Specification stability is not guaranteed.** RC fields and behaviors MAY change before v1.0 final. RCs are intended for early integrators willing to track changes.
- **Trademark "WCP-conformant" is pre-v1.0.** See `TRADEMARK_POLICY.md` for the non-enforcement commitment.

## Versioning the operator guide and documentation

- `operator-guide/` is versioned independently as RECOMMENDED practice, not normative. Major releases of the operator guide track major spec releases.
- `docs/` is versioned per build of the documentation site; the spec version they cover is named on each page.

## Backporting

Security and privacy fixes MAY be backported across MAJOR lines for the duration of LTS support (defined per release; current intent for v1.0 LTS is 36 months from v1.0 final).
