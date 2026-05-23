"""Tests for the attestation verifier.

KEY PROPERTY UNDER TEST: the verifier discriminates by (mode, kind), NOT by
worker class. The same code path passes evidence from a human worker (phone
GPS) and from a robot (indoor pose). Worker-class agnosticism is the load-
bearing D4 win.
"""
from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from wcp_coordinator.attestation_verifier import (
    DEFAULT_REGISTRY,
    evaluate_threshold,
    verify_single,
)


def test_sensor_witness_accepts_human_gps_track():
    payload = {
        "track": [
            {"t": "2026-06-01T10:00:00Z", "x": 1.0, "y": 2.0},
            {"t": "2026-06-01T10:01:00Z", "x": 1.1, "y": 2.1},
        ]
    }
    o = verify_single(
        mode="sensor-witness",
        kind="gps_track",
        payload=payload,
        task_payload={},
        schema_registry_kinds=DEFAULT_REGISTRY,
    )
    assert o.decision == "pass"


def test_sensor_witness_accepts_robot_indoor_pose_track():
    """Robot odometry verifies through the SAME code path as human GPS."""
    payload = {
        "track": [
            {"t": "2026-06-01T10:00:00Z", "x": 1.0, "y": 2.0},
            {"t": "2026-06-01T10:01:00Z", "x": 1.1, "y": 2.1},
        ]
    }
    o = verify_single(
        mode="sensor-witness",
        kind="indoor_pose_track",
        payload=payload,
        task_payload={},
        schema_registry_kinds=DEFAULT_REGISTRY,
    )
    assert o.decision == "pass"


def test_sensor_witness_rejects_empty_track():
    o = verify_single(
        mode="sensor-witness",
        kind="gps_track",
        payload={"track": []},
        task_payload={},
        schema_registry_kinds=DEFAULT_REGISTRY,
    )
    assert o.decision == "fail"


def test_unknown_mode_fails():
    o = verify_single(
        mode="not-a-mode",
        kind="anything",
        payload={},
        task_payload={},
        schema_registry_kinds=DEFAULT_REGISTRY,
    )
    assert o.decision == "fail"


def test_unregistered_kind_fails():
    o = verify_single(
        mode="sensor-witness",
        kind="not-a-kind",
        payload={},
        task_payload={},
        schema_registry_kinds=DEFAULT_REGISTRY,
    )
    assert o.decision == "fail"


def test_customer_signature_pass():
    o = verify_single(
        mode="third-party-witness",
        kind="customer_signature",
        payload={
            "signed_text": "Work completed.",
            "signature_image_hash": "abc123",
        },
        task_payload={},
        schema_registry_kinds=DEFAULT_REGISTRY,
    )
    assert o.decision == "pass"


def test_customer_signature_empty_text_fails():
    o = verify_single(
        mode="third-party-witness",
        kind="customer_signature",
        payload={"signed_text": "   ", "signature_image_hash": "abc"},
        task_payload={},
        schema_registry_kinds=DEFAULT_REGISTRY,
    )
    assert o.decision == "fail"


def test_cryptographic_presence_short_duration_review():
    payload = {
        "check_in_at": "2026-06-01T10:00:00+00:00",
        "check_out_at": "2026-06-01T10:30:00+00:00",
        "region": {"polygon": [[0, 0], [10, 0], [10, 10], [0, 10]]},
    }
    o = verify_single(
        mode="cryptographic-presence",
        kind="geofence_check_in_out",
        payload=payload,
        task_payload={"duration_minutes": 45},
        schema_registry_kinds=DEFAULT_REGISTRY,
    )
    # 30 minutes < 90% of 45 (40.5 min) -> review.
    assert o.decision == "review"


def test_cryptographic_presence_full_duration_pass():
    payload = {
        "check_in_at": "2026-06-01T10:00:00+00:00",
        "check_out_at": "2026-06-01T10:46:00+00:00",
        "region": {"polygon": [[0, 0], [10, 0], [10, 10], [0, 10]]},
    }
    o = verify_single(
        mode="cryptographic-presence",
        kind="geofence_check_in_out",
        payload=payload,
        task_payload={"duration_minutes": 45},
        schema_registry_kinds=DEFAULT_REGISTRY,
    )
    assert o.decision == "pass"


def test_owner_signoff_whatsapp_pass():
    o = verify_single(
        mode="owner-sign-off",
        kind="whatsapp_business_signed_link",
        payload={
            "signing_party_did": "did:wcp:customer",
            "signed_token": "tok123",
            "issued_at": "2026-06-01T10:45:00Z",
        },
        task_payload={},
        schema_registry_kinds=DEFAULT_REGISTRY,
    )
    assert o.decision == "pass"


def test_self_attestation_blocked_unless_explicit():
    o = verify_single(
        mode="owner-sign-off",
        kind="self_attestation_with_waiver",
        payload={"waiver_text": "I confirm", "signed_by_worker": "did:wcp:..."},
        task_payload={},  # no flag
        schema_registry_kinds=DEFAULT_REGISTRY,
    )
    assert o.decision == "fail"


# --- threshold tests -------------------------------------------------------


def test_threshold_M_of_N_pass():
    from wcp_coordinator.attestation_verifier import VerificationOutcome

    req = {"threshold": "M-of-N", "M": 2, "N": 3}
    outcomes = [
        ("sensor-witness", VerificationOutcome("pass")),
        ("third-party-witness", VerificationOutcome("pass")),
        ("owner-sign-off", VerificationOutcome("fail", reasons=("x",))),
    ]
    o = evaluate_threshold(requirement=req, outcomes=outcomes)
    assert o.decision == "pass"


def test_threshold_M_of_N_review_when_borderline():
    from wcp_coordinator.attestation_verifier import VerificationOutcome

    req = {"threshold": "M-of-N", "M": 2, "N": 3}
    outcomes = [
        ("sensor-witness", VerificationOutcome("pass")),
        ("third-party-witness", VerificationOutcome("review")),
        ("owner-sign-off", VerificationOutcome("review")),
    ]
    o = evaluate_threshold(requirement=req, outcomes=outcomes)
    assert o.decision == "review"


def test_threshold_M_greater_than_N_fails():
    from wcp_coordinator.attestation_verifier import VerificationOutcome

    req = {"threshold": "M-of-N", "M": 5, "N": 2}
    o = evaluate_threshold(requirement=req, outcomes=[])
    assert o.decision == "fail"


# --- property-based tests -------------------------------------------------


@given(
    n_pass=st.integers(min_value=0, max_value=5),
    n_fail=st.integers(min_value=0, max_value=5),
    n_review=st.integers(min_value=0, max_value=5),
    m=st.integers(min_value=1, max_value=5),
)
def test_property_threshold_M_of_N(n_pass, n_fail, n_review, m):
    from wcp_coordinator.attestation_verifier import VerificationOutcome

    total = n_pass + n_fail + n_review
    n = max(total, 1)
    if m > n:
        return
    outcomes = (
        [("sensor-witness", VerificationOutcome("pass"))] * n_pass
        + [("sensor-witness", VerificationOutcome("fail"))] * n_fail
        + [("sensor-witness", VerificationOutcome("review"))] * n_review
    )
    req = {"threshold": "M-of-N", "M": m, "N": n}
    o = evaluate_threshold(requirement=req, outcomes=outcomes)
    if n_pass >= m:
        assert o.decision == "pass"
    elif n_fail == 0 and n_pass + n_review >= m:
        assert o.decision == "review"
    else:
        assert o.decision == "fail"
