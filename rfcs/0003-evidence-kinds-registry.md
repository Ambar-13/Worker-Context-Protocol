# RFC 0003: Evidence Kinds Registry (schema registry)

- Author(s): Rentably (principal)
- Status: accepted
- Type: standards-track
- Created: 2026-05-23
- Targets: v0.1 with rolling extensions

## Summary

This RFC defines the schema registry of allowed `(mode, kind)` pairs for `AttestationEvidence`. The registry lives in this RFC, not in `spec/0.1.md`, so the spec can stay under its 30-page cap while the set of evidence kinds grows by RFC over time.

## Motivation

The four attestation modes (`sensor-witness`, `third-party-witness`, `cryptographic-presence`, `owner-sign-off`) are fixed in v0.1. The set of kinds within each mode is open-ended and benefits from extension by community contribution. Putting the registry here means a new kind ships as an RFC PR, not a spec rewrite.

## Registry at v0.1

### sensor-witness

| Kind | Description | Required payload fields |
|---|---|---|
| `gps_track` | A sequence of timestamped GPS samples | `track[]` with `t,x,y` (lat,lon or local-frame coords) |
| `indoor_pose_track` | Robot odometry track in venue-map frame | `track[]` with `t,x,y` |
| `weight_delta` | Before/after weight measurement | `before_kg`, `after_kg` |
| `photo_with_exif` | A photo with EXIF metadata | `photo_hash`, `exif` (must include `datetime`) |
| `signed_sensor_recording` | A signed sensor recording (camera, IMU, lidar) | `recording_hash`, `duration_seconds` |
| `coverage_map` | A coverage polygon over the task scope | `covered_polygon` |
| `gps_stamped_checkpoint_coverage` | GPS-stamped checkpoint hits | `checkpoints[]` |

### third-party-witness

| Kind | Description | Required payload fields |
|---|---|---|
| `customer_signature` | Customer signature on a contractor or robot delivery | `signed_text`, `signature_image_hash` |
| `phone_app_attestation` | A third-party phone app signs an attestation | `attesting_app_did`, `attestation_payload_hash` |
| `iot_beacon_proximity` | An IoT beacon installed at the venue confirms proximity | `beacon_id`, `rssi`, `observed_at` |

### cryptographic-presence

| Kind | Description | Required payload fields |
|---|---|---|
| `pose_bounded_presence_proof` | Robot odometry within a declared region for a duration | `check_in_at`, `check_out_at`, `region` |
| `geofence_check_in_out` | Phone GPS samples bracketing the required duration | `check_in_at`, `check_out_at`, `region` |

### owner-sign-off

| Kind | Description | Required payload fields |
|---|---|---|
| `self_attestation_with_waiver` | Worker self-attests; requires `self_attestation_explicitly_allowed=true` in task_payload | `waiver_text`, `signed_by_worker` |
| `whatsapp_business_signed_link` | Customer signs via a WhatsApp Business signed link | `signing_party_did`, `signed_token`, `issued_at` |

## Adding a new kind

1. Submit a PR against this RFC adding a row to the table.
2. Cite the structural property the new kind verifies and the worker class(es) where it applies (though the verifier does not branch on class).
3. Include a reference implementation in `wcp_coordinator.attestation_verifier.<mode>` and tests.

## Drawbacks

Registry growth requires discipline to avoid duplicate kinds. A new kind that overlaps an existing one should be rejected with a comment pointing to the existing one.

## External trust-root family

The evidence kind family `external-trust-root.<root-identifier>` is registered separately from the per-mode kinds above. It covers evidence signed against trust roots outside the `did:wcp` method (X.509 chains, JWKS endpoints, non-`did:wcp` DIDs). The family is governed by RFC 0034 (External Trust-Root Signed Evidence); new entries in this family are proposed via the RFC process and append to RFC 0034's per-root registration table rather than to the per-mode table in this RFC.

## Prior art

OpenID Connect's claims registry uses a similar RFC-extensible approach.

## Unresolved questions

- Should kinds carry a `confidence_class` field (e.g., for indoor pose where GPS is unavailable)?
- Should a kind declare its expected verification latency for time-bounded tasks?

## Implementation track

The `DEFAULT_REGISTRY` constant in `wcp_coordinator/attestation_verifier/__init__.py` mirrors this table. Tests in `wcp_coordinator/tests/test_attestation_verifier.py` exercise representative kinds across both worker classes.
