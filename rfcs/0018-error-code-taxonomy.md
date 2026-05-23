# RFC 0018: Error Code Taxonomy

- Author(s): Rentably (principal)
- Status: accepted (part of v0.2); amended at v0.955 (the -44xxx settlement range is removed; the -47xxx recheck range and the -42010 INVALID_DESCRIPTOR code are added — see `spec/error-codes.md`).
- Type: standards-track

## Summary

Adopts the error code taxonomy in `spec/error-codes.md`: numeric ranges by category (-32xxx standard, -40xxx identity, -41xxx attestation, -42xxx task lifecycle, -43xxx execution, -45xxx scope, -46xxx policy, -47xxx recheck, -5xxxx federation, -6xxxx conformance). The -44xxx range previously carried settlement errors and was removed at v0.955. Symbols namespaced under `wcp.error`. Structured retry semantics per error.

## Drawbacks

The wide numeric range invites operator-defined codes that may collide. Section "-8xxxx Operator-defined" addresses this by reserving a range; the conformance suite verifies that conformant implementations do not emit codes in the operator range under standard flows.

## Prior art

- JSON-RPC 2.0 error code conventions
- HTTP status code taxonomy
- Stripe API error code structure (https://stripe.com/docs/api/errors)

## Implementation track

`error-codes.md` is the artifact; the coordinator reference and SDKs use the constants from this taxonomy.
