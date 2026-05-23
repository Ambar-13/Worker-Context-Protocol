# RFC 0018: Error Code Taxonomy

- Author(s): Rentably (principal)
- Status: accepted (part of v1.0-rc1)
- Type: standards-track

## Summary

Adopts the error code taxonomy in `spec/error-codes.md`: numeric ranges by category (-32xxx standard, -40xxx identity, -41xxx attestation, -42xxx task lifecycle, -43xxx execution, -44xxx settlement, -45xxx scope, -46xxx policy, -5xxxx federation, -6xxxx conformance). Symbols namespaced under `wcp.error`. Structured retry semantics per error.

## Drawbacks

The wide numeric range invites operator-defined codes that may collide. Section "-8xxxx Operator-defined" addresses this by reserving a range; the conformance suite verifies that conformant implementations do not emit codes in the operator range under standard flows.

## Prior art

- JSON-RPC 2.0 error code conventions
- HTTP status code taxonomy
- Stripe API error code structure (https://stripe.com/docs/api/errors)

## Implementation track

`error-codes.md` is the artifact; the coordinator reference and SDKs use the constants from this taxonomy.
