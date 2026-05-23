"""owner-sign-off verifier.

The "owner" here is the customer or named accountable party for the task,
NOT the worker's principal. (For human contractors, this is the MCST
representative or building manager; for robots, this is the receiving
customer at the dropoff.) Worker self-attestation with a signed waiver is
permitted only when explicitly declared by the task.
"""
from __future__ import annotations

from typing import Any


def verify(kind: str, payload: dict[str, Any], *, task_payload: dict[str, Any]):
    from . import VerificationOutcome

    if kind == "whatsapp_business_signed_link":
        for r in ("signing_party_did", "signed_token", "issued_at"):
            if r not in payload:
                return VerificationOutcome(
                    decision="fail",
                    reasons=(
                        f"whatsapp_business_signed_link missing field: {r}",
                    ),
                )
        return VerificationOutcome(decision="pass")

    if kind == "self_attestation_with_waiver":
        if not task_payload.get("self_attestation_explicitly_allowed"):
            return VerificationOutcome(
                decision="fail",
                reasons=(
                    "self_attestation_with_waiver requires explicit "
                    "self_attestation_explicitly_allowed flag in task_payload",
                ),
            )
        for r in ("waiver_text", "signed_by_worker"):
            if r not in payload:
                return VerificationOutcome(
                    decision="fail",
                    reasons=(
                        f"self_attestation_with_waiver missing field: {r}",
                    ),
                )
        return VerificationOutcome(decision="pass")

    return VerificationOutcome(
        decision="fail",
        reasons=(f"owner-sign-off verifier: unknown kind {kind}",),
    )
