"""
Attestation verifier package.

THIS PACKAGE IS THE SINGLE POINT AT WHICH WORKER-CLASS AGNOSTICISM IS
MECHANICALLY CHECKED. The verifier discriminates by (mode, kind), never by
worker class. A human's phone GPS track and a robot's odometry are both
`sensor-witness` evidence; they differ only by `kind`. The verifier accepts
both with identical code paths. This is the load-bearing D4 win.

If you find yourself adding a `if worker_class == ...` branch in this
package, stop. That branch belongs in the application-layer descriptor,
not in the verifier.

Verifier dispatch:
    sensor-witness        -> sensor_witness.verify
    third-party-witness   -> third_party_witness.verify
    cryptographic-presence -> cryptographic_presence.verify
    owner-sign-off        -> owner_signoff.verify

Each verifier returns a VerificationOutcome with (decision, residual, reasons).
The aggregate verifier evaluates the M-of-N threshold across modes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from . import (
    cryptographic_presence,
    owner_signoff,
    sensor_witness,
    third_party_witness,
)


@dataclass(frozen=True)
class VerificationOutcome:
    decision: str  # "pass" | "fail" | "review"
    residual: dict[str, Any] = field(default_factory=dict)
    reasons: tuple[str, ...] = ()


_DISPATCH = {
    "sensor-witness": sensor_witness.verify,
    "third-party-witness": third_party_witness.verify,
    "cryptographic-presence": cryptographic_presence.verify,
    "owner-sign-off": owner_signoff.verify,
}


def verify_single(
    mode: str,
    kind: str,
    payload: dict[str, Any],
    *,
    task_payload: dict[str, Any],
    schema_registry_kinds: dict[str, set[str]],
) -> VerificationOutcome:
    """Verify one piece of evidence.

    Discriminates by (mode, kind) only. NO worker-class branching.
    """
    if mode not in _DISPATCH:
        return VerificationOutcome(
            decision="fail", reasons=(f"unknown mode: {mode}",)
        )
    allowed_kinds = schema_registry_kinds.get(mode, set())
    if kind not in allowed_kinds:
        return VerificationOutcome(
            decision="fail",
            reasons=(f"kind {kind!r} not registered for mode {mode!r}",),
        )
    return _DISPATCH[mode](kind, payload, task_payload=task_payload)


def evaluate_threshold(
    *,
    requirement: dict[str, Any],
    outcomes: list[tuple[str, VerificationOutcome]],
) -> VerificationOutcome:
    """Aggregate per-evidence outcomes against M-of-N threshold.

    `outcomes` is a list of (mode, outcome) tuples in submission order.
    """
    threshold = requirement.get("threshold", "all")
    pass_count = sum(1 for _, o in outcomes if o.decision == "pass")
    fail_count = sum(1 for _, o in outcomes if o.decision == "fail")
    review_count = sum(1 for _, o in outcomes if o.decision == "review")
    total = len(outcomes)
    all_reasons = tuple(r for _, o in outcomes for r in o.reasons)

    if threshold == "any":
        if pass_count >= 1:
            return VerificationOutcome(decision="pass")
        if review_count >= 1 and fail_count == 0:
            return VerificationOutcome(
                decision="review", reasons=all_reasons
            )
        return VerificationOutcome(decision="fail", reasons=all_reasons)

    if threshold == "all":
        if pass_count == total and total > 0:
            return VerificationOutcome(decision="pass")
        if fail_count > 0:
            return VerificationOutcome(decision="fail", reasons=all_reasons)
        return VerificationOutcome(decision="review", reasons=all_reasons)

    if threshold == "M-of-N":
        try:
            m = int(requirement["M"])
            n = int(requirement["N"])
        except (KeyError, ValueError, TypeError):
            return VerificationOutcome(
                decision="fail",
                reasons=("M-of-N threshold requires integer M and N",),
            )
        if m > n:
            return VerificationOutcome(
                decision="fail", reasons=(f"M > N ({m} > {n})",)
            )
        if pass_count >= m:
            return VerificationOutcome(decision="pass")
        possible = pass_count + review_count
        if possible >= m and fail_count == 0:
            return VerificationOutcome(decision="review", reasons=all_reasons)
        return VerificationOutcome(decision="fail", reasons=all_reasons)

    return VerificationOutcome(
        decision="fail", reasons=(f"unknown threshold: {threshold}",)
    )


# Default schema registry used by tests; production loads from RFC 0003.
DEFAULT_REGISTRY: dict[str, set[str]] = {
    "sensor-witness": {
        "gps_track",
        "indoor_pose_track",
        "manipulator_pose_track",  # added at v0.95 for embodied-agent robot work
        "weight_delta",
        "photo_with_exif",
        "signed_sensor_recording",
        "coverage_map",
        "gps_stamped_checkpoint_coverage",
        "thermal_image_capture_manifest",  # paper §3.1 example
    },
    "third-party-witness": {
        "customer_signature",
        "phone_app_attestation",
        "iot_beacon_proximity",
        "inspection_checklist_signed",  # paper §3.1 example
    },
    "cryptographic-presence": {
        "pose_bounded_presence_proof",
        "geofence_check_in_out",
        "cryptographic_nonce_exchange",  # paper §4 unified kind
    },
    "owner-sign-off": {
        "self_attestation_with_waiver",
        "whatsapp_business_signed_link",
    },
}
