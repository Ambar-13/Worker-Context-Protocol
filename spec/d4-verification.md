# D4 Forcing Function Verification

**Status:** verified pass for v0.1 publication. Historical: the original v0.1 verification walks the nine RPCs including `tasks/settle`; at v0.955 the RPC surface contracts to eight and the `tasks/settle` step in each scenario is replaced by an audit-chain `task_completed` event consumed by an external settlement layer. The D4 conclusion (one RPC surface for every cell) is unchanged.
**Date:** 2026-05-23

The D4 forcing function is the design-quality gate before WCP v0.1 publication: three application-layer task descriptors x two worker classes = six cells. Each cell MUST be expressible using the nine RPCs in `spec/0.1.md` without modification. If any cell would force a tenth RPC or a new top-level RPC parameter, the surface is wrong and the spec iterates before publication.

This document walks each of the six cells. **Result: all six pass.** No new RPCs required; no parameter modifications. Variance lives inside `attestation_requirement.evidence_schema` (which is itself an extensible typed object, RFC-extensible via the schema registry) and inside the opaque `descriptor_payload`.

---

## Cell A1: transport / autonomous_robot

**Scenario.** An AMR delivers a 12 kg toolbox across a sub-50k sqft building from basement (pose [2.0, 1.5, 0]) to unit 12-04 (pose [-3.0, 4.0, 0]).

**TaskDescriptor (excerpt):**

```json
{
  "descriptor_type": "transport",
  "descriptor_payload": {
    "pickup":  { "venue_id": "v1", "map_id": "m1", "pose": [2.0, 1.5, 0] },
    "dropoff": { "venue_id": "v1", "map_id": "m1", "pose": [-3.0, 4.0, 0] },
    "payload_description": "12 kg toolbox",
    "handoff_protocol": "customer_signature"
  },
  "attestation_requirement": {
    "modes": ["sensor-witness", "third-party-witness"],
    "threshold": "M-of-N", "M": 2, "N": 2,
    "evidence_schema": [
      { "mode": "sensor-witness", "kinds": ["indoor_pose_track"] },
      { "mode": "third-party-witness", "kinds": ["customer_signature"] }
    ]
  }
}
```

**RPC walk:**

1. agent: `tasks/post` with the descriptor.
2. AMR: `capabilities/list` published; AMR is matched.
3. AMR: `tasks/claim` with `acceptance_attestation`.
4. AMR: `tasks/execute`; emits `picked_up` then `arrived_at_dropoff`.
5. AMR: `tasks/attest` with `[{mode:sensor-witness, kind:indoor_pose_track, ...}, {mode:third-party-witness, kind:customer_signature, ...}]`.
6. Verifier passes (M=2 of N=2).
7. coordinator: `tasks/settle` with split.

**Surface check.** No new RPC. No new parameter.

---

## Cell A2: transport / human

**Scenario.** A Rentably contractor walks a replacement smoke detector from the building basement to unit 12-04.

**TaskDescriptor (excerpt):**

```json
{
  "descriptor_type": "transport",
  "descriptor_payload": {
    "pickup":  { "venue_id": "v1", "address": "Basement, Store Room A" },
    "dropoff": { "venue_id": "v1", "address": "Unit 12-04" },
    "payload_description": "Replacement smoke detector",
    "handoff_protocol": "customer_signature_on_phone"
  },
  "attestation_requirement": {
    "modes": ["sensor-witness", "third-party-witness"],
    "threshold": "M-of-N", "M": 2, "N": 2,
    "evidence_schema": [
      { "mode": "sensor-witness", "kinds": ["gps_track"] },
      { "mode": "third-party-witness", "kinds": ["customer_signature"] }
    ]
  }
}
```

**RPC walk.** Identical to A1. The only difference is the `evidence_schema.kinds`: `gps_track` (phone) replaces `indoor_pose_track` (robot odometry). The verifier accepts both kinds under `sensor-witness`, discriminating by kind not by worker class. This is the D4 win on the human-robot axis.

**Surface check.** No new RPC. No new parameter. The `gps_track` kind is registered in RFC 0003.

---

## Cell B1: scheduled_presence / autonomous_robot

**Scenario.** A cleaning robot is present in the lobby for 45 minutes between 02:00-04:00 SGT, performs an overnight floor clean, takes pre-clean and post-clean photos.

**TaskDescriptor (excerpt):**

```json
{
  "descriptor_type": "scheduled_presence",
  "descriptor_payload": {
    "location": { "venue_id": "v1", "zone_id": "lobby" },
    "duration_minutes": 45,
    "activity_class": "overnight_floor_clean",
    "checklist": ["pre_clean_photo", "post_clean_photo"]
  },
  "constraints": {
    "time_window": { "earliest": "02:00", "latest": "04:00", "timezone": "Asia/Singapore" }
  },
  "attestation_requirement": {
    "modes": ["cryptographic-presence", "sensor-witness"],
    "threshold": "M-of-N", "M": 2, "N": 2,
    "evidence_schema": [
      { "mode": "cryptographic-presence", "kinds": ["pose_bounded_presence_proof"] },
      { "mode": "sensor-witness", "kinds": ["photo_with_exif"] }
    ]
  }
}
```

**RPC walk.** Standard. The robot publishes capabilities, claims, opens execute, emits checkpoint events for the two photos, then attests with the presence proof and photo bundle hash.

**Surface check.** No new RPC.

---

## Cell B2: scheduled_presence / human

**Scenario.** The live Rentably wedge. A quarterly aircon service contractor is at an MCST unit for 45 minutes, performs the standard service checklist, gets MCST representative sign-off.

**TaskDescriptor (excerpt):**

```json
{
  "descriptor_type": "scheduled_presence",
  "descriptor_payload": {
    "location": { "venue_id": "v1", "unit_id": "12-04" },
    "duration_minutes": 45,
    "activity_class": "quarterly_aircon_service",
    "checklist": ["filter_check", "refrigerant_check", "drain_check", "operational_test"]
  },
  "attestation_requirement": {
    "modes": ["cryptographic-presence", "owner-sign-off"],
    "threshold": "M-of-N", "M": 2, "N": 2,
    "evidence_schema": [
      { "mode": "cryptographic-presence", "kinds": ["geofence_check_in_out"] },
      { "mode": "owner-sign-off", "kinds": ["whatsapp_business_signed_link"] }
    ]
  }
}
```

**RPC walk.** Identical RPC sequence. The presence proof is a `geofence_check_in_out` (phone GPS bounded to venue polygon) rather than `pose_bounded_presence_proof` (robot odometry). The owner sign-off is via a WhatsApp Business signed link rather than a robot-side proof.

**Surface check.** No new RPC. The same `attestation_requirement` shape, populated with different kinds. The verifier accepts both `geofence_check_in_out` and `pose_bounded_presence_proof` under `cryptographic-presence` mode, again by kind not class.

---

## Cell C1: observe_and_report / autonomous_robot

**Scenario.** A drone or AMR collects CO2 readings across a polygon zone.

**TaskDescriptor (excerpt):**

```json
{
  "descriptor_type": "observe_and_report",
  "descriptor_payload": {
    "scope": { "venue_id": "v1", "polygon": [[0,0],[10,0],[10,5],[0,5]] },
    "sensor_classes": ["co2", "rgb_camera"],
    "sampling": "every 10m or 30s",
    "deliverable_schema": "wcp/observation/0.1"
  },
  "attestation_requirement": {
    "modes": ["sensor-witness"],
    "threshold": "M-of-N", "M": 1, "N": 1,
    "evidence_schema": [
      { "mode": "sensor-witness", "kinds": ["signed_sensor_recording", "coverage_map"] }
    ]
  }
}
```

**Surface check.** No new RPC.

---

## Cell C2: observe_and_report / human

**Scenario.** A fire-safety inspector walks a corridor checklist, takes timestamped photos at named checkpoints.

**TaskDescriptor (excerpt):**

```json
{
  "descriptor_type": "observe_and_report",
  "descriptor_payload": {
    "scope": { "venue_id": "v1", "corridor_ids": ["c1", "c2", "c3"] },
    "sensor_classes": ["rgb_camera"],
    "sampling": "per checkpoint",
    "deliverable_schema": "wcp/observation/0.1"
  },
  "attestation_requirement": {
    "modes": ["sensor-witness"],
    "threshold": "M-of-N", "M": 1, "N": 1,
    "evidence_schema": [
      { "mode": "sensor-witness",
        "kinds": ["photo_with_exif", "gps_stamped_checkpoint_coverage"] }
    ]
  }
}
```

**Surface check.** No new RPC.

---

## Hard-case probe: the AMR-handoff-to-stationary-manipulator (Scenario 13 boundary)

A common objection: "What if an AMR transports a package to a destination where a stationary manipulator must place it on a shelf?" Naive reading: this requires subcontracting (the AMR claims `transport` and delegates the final-shelf-placement to the manipulator).

Under v0.1 (subcontracting forbidden at worker layer, RFC 0002 tracking), the agent expresses this as **two tasks at the agent layer**:

1. `transport(pickup, intermediate_dropoff)` claimed by the AMR.
2. `manipulate_and_place(intermediate_location, shelf_pose)` claimed by the stationary manipulator.

Each task uses the standard nine-RPC surface. Each has its own attestation_requirement, its own settlement split. The agent or platform handles the choreography; WCP does not.

**Surface check.** No new RPC. The composition lives outside WCP. RFC 0002 will revisit at v0.2 once deployment evidence accumulates on whether worker-layer delegation is genuinely needed or whether agent-layer composition suffices.

---

## Conclusion

All six D4 cells pass. The hard-case (AMR-to-manipulator) is expressible via agent-layer composition without new primitives. **The v0.1 RPC surface is locked.**

Variance is contained inside:

- `attestation_requirement.evidence_schema` (extensible by RFC 0003).
- `descriptor_payload` (opaque to RPC layer; application-defined).
- `class_extension` on CapabilityDescriptor (opaque to RPC layer; application-defined).

No RPC, no top-level TaskDescriptor parameter, no CapabilityDescriptor required-block field is contingent on worker class.
