"""sensor-witness verifier.

Accepts ALL sensor evidence kinds, regardless of worker class. A human's
phone GPS track and a robot's odometry-derived indoor pose track verify
through the same code path.
"""
from __future__ import annotations

from typing import Any


def verify(
    kind: str, payload: dict[str, Any], *, task_payload: dict[str, Any]
):
    from . import VerificationOutcome

    if kind in ("gps_track", "indoor_pose_track"):
        track = payload.get("track")
        if not isinstance(track, list) or len(track) == 0:
            return VerificationOutcome(
                decision="fail", reasons=("empty or missing track",)
            )
        for sample in track:
            if not isinstance(sample, dict):
                return VerificationOutcome(
                    decision="fail",
                    reasons=("track sample must be an object",),
                )
            for required_field in ("t", "x", "y"):
                if required_field not in sample:
                    return VerificationOutcome(
                        decision="fail",
                        reasons=(
                            f"track sample missing field: {required_field}",
                        ),
                    )
        return VerificationOutcome(decision="pass")

    if kind == "weight_delta":
        before = payload.get("before_kg")
        after = payload.get("after_kg")
        if before is None or after is None:
            return VerificationOutcome(
                decision="fail",
                reasons=("weight_delta requires before_kg and after_kg",),
            )
        if not isinstance(before, (int, float)) or not isinstance(
            after, (int, float)
        ):
            return VerificationOutcome(
                decision="fail",
                reasons=("before_kg and after_kg must be numeric",),
            )
        return VerificationOutcome(decision="pass")

    if kind == "photo_with_exif":
        hash_hex = payload.get("photo_hash")
        exif = payload.get("exif")
        if not hash_hex or not exif:
            return VerificationOutcome(
                decision="fail",
                reasons=("photo_with_exif requires photo_hash and exif",),
            )
        if "datetime" not in exif:
            return VerificationOutcome(
                decision="review", reasons=("exif missing datetime",)
            )
        return VerificationOutcome(decision="pass")

    if kind == "signed_sensor_recording":
        if "recording_hash" not in payload or "duration_seconds" not in payload:
            return VerificationOutcome(
                decision="fail",
                reasons=(
                    "signed_sensor_recording requires recording_hash and duration_seconds",
                ),
            )
        return VerificationOutcome(decision="pass")

    if kind in ("coverage_map", "gps_stamped_checkpoint_coverage"):
        if "covered_polygon" not in payload and "checkpoints" not in payload:
            return VerificationOutcome(
                decision="fail",
                reasons=(
                    "coverage evidence requires covered_polygon or checkpoints",
                ),
            )
        return VerificationOutcome(decision="pass")

    return VerificationOutcome(
        decision="fail", reasons=(f"sensor-witness verifier: unknown kind {kind}",)
    )
