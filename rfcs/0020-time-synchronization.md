# RFC 0020: Time Synchronization

- Author(s): Rentably (principal)
- Status: accepted (part of v0.2)
- Type: standards-track

## Summary

Adopts `spec/time-synchronization.md`: canonical time source declaration per coordinator, drift tolerances per operation, NTP requirements, timestamp authority for the audit chain, leap-second policy (smear preferred).

## Drawbacks

Strict drift tolerances may flag legitimate edge cases (a contractor in a deep basement with no GPS or NTP). Mitigation: review path for evidence with `collected_at` outside the 24-hour window.

## Prior art

- Google's leap-second smear (https://developers.google.com/time/smear)
- Cloudflare Roughtime
- Spanner's TrueTime (the structural cousin for typed-uncertainty design in WCP, applied at a coarser granularity here)

## Implementation track

`time-synchronization.md` is the artifact. Coordinator publishes `wcp:metadata.canonical_time_source` and `wcp:metadata.leap_second_policy` in its DID document.
