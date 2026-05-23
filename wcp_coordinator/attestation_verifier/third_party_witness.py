"""third-party-witness verifier.

Examples: customer signature on a contractor PWA, IoT beacon proximity ping
from a building's installed beacon, phone-app attestation from a third-party
app the customer trusts.

The verifier does not care if the third party is a phone or a beacon. It
discriminates by `kind`.
"""
from __future__ import annotations

from typing import Any


def verify(kind: str, payload: dict[str, Any], *, task_payload: dict[str, Any]):
    from . import VerificationOutcome

    if kind == "customer_signature":
        required = ("signed_text", "signature_image_hash")
        for r in required:
            if r not in payload:
                return VerificationOutcome(
                    decision="fail",
                    reasons=(f"customer_signature missing field: {r}",),
                )
        # signed_text MAY contain a per-task confirmation string; we only check
        # presence and non-empty.
        if not payload["signed_text"].strip():
            return VerificationOutcome(
                decision="fail", reasons=("signed_text is empty",)
            )
        return VerificationOutcome(decision="pass")

    if kind == "phone_app_attestation":
        for r in ("attesting_app_did", "attestation_payload_hash"):
            if r not in payload:
                return VerificationOutcome(
                    decision="fail",
                    reasons=(f"phone_app_attestation missing field: {r}",),
                )
        return VerificationOutcome(decision="pass")

    if kind == "iot_beacon_proximity":
        for r in ("beacon_id", "rssi", "observed_at"):
            if r not in payload:
                return VerificationOutcome(
                    decision="fail",
                    reasons=(f"iot_beacon_proximity missing field: {r}",),
                )
        return VerificationOutcome(decision="pass")

    return VerificationOutcome(
        decision="fail",
        reasons=(f"third-party-witness verifier: unknown kind {kind}",),
    )
