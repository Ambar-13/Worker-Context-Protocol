"""cryptographic-presence verifier.

Examples: a robot's pose-bounded presence proof (signed odometry within a
declared geofence over a duration); a human's phone geofence check-in/out
(signed location samples bracketing the required duration).

Discriminates by `kind`; not by worker class. The shared structural property
is "presence within a region for a duration, cryptographically signed."
"""
from __future__ import annotations

from datetime import datetime
from typing import Any


def _parse_iso(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def verify(kind: str, payload: dict[str, Any], *, task_payload: dict[str, Any]):
    from . import VerificationOutcome

    if kind in ("pose_bounded_presence_proof", "geofence_check_in_out"):
        for r in ("check_in_at", "check_out_at", "region"):
            if r not in payload:
                return VerificationOutcome(
                    decision="fail",
                    reasons=(f"{kind} missing field: {r}",),
                )
        try:
            t_in = _parse_iso(payload["check_in_at"])
            t_out = _parse_iso(payload["check_out_at"])
        except ValueError as exc:
            return VerificationOutcome(
                decision="fail",
                reasons=(f"check_in/out timestamp parse: {exc}",),
            )
        if t_out <= t_in:
            return VerificationOutcome(
                decision="fail",
                reasons=("check_out_at must be strictly after check_in_at",),
            )
        # Optional check against task duration if descriptor declared one.
        required_minutes = task_payload.get("duration_minutes")
        if isinstance(required_minutes, int):
            actual_minutes = (t_out - t_in).total_seconds() / 60.0
            if actual_minutes + 1e-6 < required_minutes * 0.9:
                return VerificationOutcome(
                    decision="review",
                    reasons=(
                        f"presence duration {actual_minutes:.1f} minutes "
                        f"is below 90% of required {required_minutes}",
                    ),
                )
        return VerificationOutcome(decision="pass")

    return VerificationOutcome(
        decision="fail",
        reasons=(f"cryptographic-presence verifier: unknown kind {kind}",),
    )
