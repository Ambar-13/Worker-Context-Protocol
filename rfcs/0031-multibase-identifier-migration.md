# RFC 0031: Multibase Identifier Migration

- Author(s): WCP TSC
- Status: open (v1.1 candidate)
- Type: standards-track
- Created: 2026-05-23
- Targets: v1.1, v1.2 (deprecation), v2.0 (removal)

## Summary

Specifies a v1.1 evolution of the `did:wcp` identifier grammar from raw base58 (`did:wcp:<base58>`) to multibase (`did:wcp:z<base58btc-bytes>`), with a two-version compatibility window. The multibase prefix declares the encoding explicitly per draft-msporny-multibase, aligning `did:wcp` with `did:key`, `did:peer`, and other DID methods that carry raw cryptographic identifier bytes.

## Motivation

The v1.0-rc1 identifier grammar declares Ed25519 keys via base58 with no encoding prefix. This is fine when every key is 32 bytes of Ed25519, but the grammar foreseeably breaks against three realistic v1.x or v2.x extensions:

1. **Post-quantum keys.** Dilithium, SPHINCS+, and other PQ signatures produce public keys ranging from hundreds to thousands of bytes. The current spec has no way for a verifier to tell whether `did:wcp:<base58>` decodes to a 32-byte Ed25519 key or a 1952-byte Dilithium key without out-of-band context. [REASONED] PQ migration in IETF and W3C is on a 3-7 year horizon; building the prefix mechanism now is cheap insurance.
2. **Alternate encodings.** Operators in low-bandwidth contexts (subsea telemetry, satellite uplinks) may prefer base32 (RFC 4648) for case-insensitivity and DTMF compatibility. Operators in URL contexts may prefer base64url. The multibase registry already covers these.
3. **Cross-DID interop.** `did:key`, `did:peer`, and `did:cheqd` all use multibase prefixes. A WCP coordinator that federates capability discovery with non-WCP DIDs benefits from a uniform decoding path.

A second motivation is removing an implicit ecosystem-specific anchor. The v1.0-rc1 base58 alphabet comments referred to the encoding by its association with a single ecosystem (since rewritten in v1.0-rc2.1 to use the standards-grounded base58btc Multibase reference). Multibase is the W3C-and-IETF-tracked formalization; using its prefix is the explicit, neutral, future-proof choice.

## Design

### New v1.1 identifier grammar (additive)

```
did:wcp:<multibase-prefix><encoded-bytes>
```

Where `<multibase-prefix>` is a single character from the multibase registry:

| Prefix | Encoding | Notes |
|---|---|---|
| `z` | base58btc | Default for raw cryptographic identifier bytes |
| `m` | base64 | Padded |
| `u` | base64url | No padding |
| `b` | base32 | RFC 4648 |
| `f` | hex (lowercase) | RFC 4648 |

A coordinator MUST accept `z`-prefixed identifiers in v1.1. Coordinators SHOULD accept additional prefixes per operator policy.

The decoded byte sequence is interpreted per the spec's key-type rules. For Ed25519 (current default), the decoded length is 32 bytes. Future RFCs MAY register additional key types with associated decoded-length constraints.

### v1.0-rc1 backward compatibility

Identifiers issued under v1.0-rc1 (no multibase prefix; raw base58) remain valid:

- v1.1 coordinators MUST accept both `did:wcp:<base58>` (legacy) and `did:wcp:z<base58btc>` (multibase).
- v1.1 SDKs SHOULD emit a deprecation warning when generating new legacy identifiers.
- v1.2 coordinators MUST accept both forms; SDKs MUST default to multibase; legacy emission requires an explicit `legacy_identifier=True` flag.
- v2.0 coordinators MAY reject legacy identifiers with `INVALID_DID_FORMAT`.

The compatibility window is therefore three minor versions (v1.1 introduces, v1.2 default-flips, v2.0 removes). [VERIFIED] this matches the spec/semver-policy.md "at least one minor release with deprecation warning before removal" rule.

### Migration impact assessment

**Identifier persistence.** A worker's reputation lookup is keyed by the canonical identifier. v1.1 coordinators MUST canonicalize legacy identifiers to multibase form before reputation lookup, and persist the canonicalized form in their reputation index. Workers with reputation history under v1.0-rc1 transition transparently.

**Audit chain implications.** Audit chain entries record identifier strings as opaque values. The hash chain is unaffected by the identifier format change. Existing entries reference legacy identifiers; v1.1 verifiers MUST resolve both forms to the same canonical identity.

**SDK changes.** v1.1 SDKs add:
- `multibase_encode(bytes, prefix='z') -> str` and `multibase_decode(str) -> (prefix, bytes)` helpers.
- Identity constructors that accept either form; new identifiers emit multibase by default.
- A `--legacy-identifier` CLI flag (or equivalent) on `wcp init worker` for operators who need the old form for backward-compatibility testing.

**Federation impact.** Federation trust anchors reference peer coordinator DIDs. v1.1 trust anchors MAY use either form; v1.2 anchors MUST use multibase. Peer coordinators MUST canonicalize before anchor verification.

## Drawbacks

- Every implementer touches identifier parsing twice (v1.0-rc1 then v1.1). Lower bar than touching the wire protocol, but real.
- Operators with deep deployments may resist a flag day in v2.0. The three-version window is the mitigation; v2.0 can defer flag day to v2.1 if operator feedback demands.
- The multibase RFC is itself in draft (draft-msporny-multibase), not yet IETF-published. [VERIFIED, https://datatracker.ietf.org/doc/draft-msporny-multibase/]. The prefix table is stable enough to depend on; the formal RFC status is the only soft dependency.

## Alternatives

1. **Status quo (raw base58).** Forecloses post-quantum migration and cross-DID interop. Rejected.
2. **Mandatory v2.0 break.** Skip the compatibility window; v2.0 rejects all legacy identifiers. Cleaner but penalizes early adopters. Rejected; the three-version window is the consensus pattern for protocol identifier evolution (cf. semver-policy.md).
3. **Inline key-type tag (without multibase).** Define a WCP-specific prefix like `did:wcp:ed25519:<base58>`. Diverges from W3C DID-method conventions and from did:key. Rejected.

## Prior art

- Multibase RFC draft (https://datatracker.ietf.org/doc/draft-msporny-multibase/) [VERIFIED]
- did:key method spec (https://w3c-ccg.github.io/did-method-key/) uses multibase identifiers; the design pattern WCP adopts here. [VERIFIED]
- did:peer method spec uses multibase. [VERIFIED]
- RFC 0017 (semver-policy) establishes the three-version deprecation window pattern.
- W3C DID-spec-registries (https://www.w3.org/TR/did-spec-registries/) records multibase prefix conventions.

## Unresolved questions

**1. Single preferred encoding, or open registry?**

Should v1.1 mandate base58btc (`z`) as the only acceptable encoding for new identifiers, accepting other prefixes only when consuming external DIDs, or should it accept any registered multibase prefix at creation time?

Arguments for single preferred encoding:
- Reduces verifier complexity; one decode path covers all native WCP identifiers.
- Avoids subtle interop issues across implementations that support different prefix subsets.
- Aligns with did:key, which mandates `z`.

Arguments for open registry:
- Operators with specific encoding constraints (case-insensitive DTMF, URL-safe contexts, hex-debugging workflows) gain flexibility.
- Future-proofs against multibase additions without a spec rev.

**Recommendation (pending discussion):** mandate `z` as the only encoding for new identifiers in v1.1; accept other prefixes only when consuming externally issued DIDs in federation contexts. Revisit in v1.2 based on operator feedback.

**2. Canonicalization rules across federation.**

Federation peers with different multibase support levels MAY produce divergent canonical forms. The spec MUST define a canonicalization function. Recommendation: lowercase the multibase prefix, decode to bytes, re-encode to base58btc with `z` prefix.

**3. Trust-class declaration interaction.**

RFC 0033 (Attestation Key Trust Classes) introduces an optional `trust_class` field. Does multibase migration interact with trust class? Specifically: should hardware-attested keys be required to use a particular encoding (e.g., one that matches the attestation envelope's native encoding)? Recommendation: no special-casing; trust class is orthogonal to encoding. RFC 0033 to confirm.

## Implementation track

v1.1 reference SDK changes:
- `wcp_sdk/identity.py`: `WorkerIdentity.from_did(s: str)` accepts both forms; canonicalizes internally
- `wcp_sdk_typescript/src/identity.ts`: equivalent
- `wcp_sdk_rust/src/identity.rs`, `wcp_sdk_go/identity.go`: equivalent
- `wcp_coordinator/did_resolver.py`: dual-format acceptance with canonicalization

v1.1 conformance test cases:
- Level 1: coordinator accepts both legacy and multibase identifiers
- Level 1: canonicalization is consistent across SDKs (cross-language conformance)
- Level 2: reputation lookups resolve both forms to the same identity

v1.2 deprecation warning:
- SDK emits `wcp.deprecation.legacy_identifier_emission` when generating a legacy identifier without explicit opt-in

v2.0 removal:
- SDK and coordinator reject legacy identifiers with `INVALID_DID_FORMAT` (error code TBD, see spec/error-codes.md)
