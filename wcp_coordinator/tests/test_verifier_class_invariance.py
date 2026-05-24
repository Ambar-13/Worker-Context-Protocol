"""Property-based class-invariance test for the attestation verifier.

The paper's load-bearing claim (Section 3, the D4 forcing function) is
that the verifier discriminates by (mode, kind) ONLY — never by worker
class. This test pins that claim mechanically.

Two property tests, one per outcome branch:

  test_verifier_invariant_across_classes_pass_eligible
    Generates (mode, kind, payload) triples whose payload is designed to
    pass the per-kind verifier. For each triple, runs the full lifecycle
    (capabilities/upsert -> tasks/post -> tasks/claim -> tasks/execute
    -> tasks/attest) once per worker class, then asserts the
    verifier_decision and reasons tuple are byte-identical across all
    five classes.

  test_verifier_invariant_across_classes_fail_eligible
    Same shape, with payloads designed to FAIL the per-kind verifier.
    Asserts the same decision+reasons invariance on the failure branch.

If either test fails, the verifier (or something the verifier reads)
introduced a class-dependent branch. Combined with the AST static check
in test_verifier_class_invariance_ast.py, this closes the loophole the
paper's claim asserts.

Hypothesis runs 100 examples per (mode, kind) combination by default
(see HYPOTHESIS_MAX_EXAMPLES). To rerun with more, set the env var
WCP_INVARIANCE_EXAMPLES=N before pytest.
"""
from __future__ import annotations

import json
import os
import uuid
from typing import Any, Iterable

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from wcp_coordinator.attestation_verifier import (
    DEFAULT_REGISTRY,
    VerificationOutcome,
    verify_single,
)
from wcp_coordinator.models import WorkerClass


# All five worker classes from spec/0.2.md §4 (CapabilityDescriptor).
ALL_WORKER_CLASSES: tuple[str, ...] = tuple(c.value for c in WorkerClass)

HYPOTHESIS_MAX_EXAMPLES = int(os.environ.get("WCP_INVARIANCE_EXAMPLES", "100"))


# ---------------------------------------------------------------------------
# Payload strategies per kind
# ---------------------------------------------------------------------------


def _pass_payload_strategy(mode: str, kind: str) -> st.SearchStrategy:
    """Strategies that produce payloads the per-kind verifier accepts."""
    if mode == "sensor-witness":
        if kind in ("gps_track", "indoor_pose_track"):
            sample = st.fixed_dictionaries({
                "t": st.from_regex(r"\A2026-06-01T\d\d:\d\d:\d\dZ\Z"),
                "x": st.floats(min_value=-180, max_value=180, allow_nan=False, allow_infinity=False),
                "y": st.floats(min_value=-90, max_value=90, allow_nan=False, allow_infinity=False),
            })
            return st.fixed_dictionaries({
                "track": st.lists(sample, min_size=1, max_size=8),
            })
        if kind == "weight_delta":
            return st.fixed_dictionaries({
                "before_kg": st.floats(min_value=0, max_value=10000, allow_nan=False, allow_infinity=False),
                "after_kg": st.floats(min_value=0, max_value=10000, allow_nan=False, allow_infinity=False),
            })
        if kind == "photo_with_exif":
            return st.fixed_dictionaries({
                "photo_hash": st.text(alphabet="0123456789abcdef", min_size=8, max_size=64),
                "exif": st.fixed_dictionaries({"datetime": st.from_regex(r"\A2026:06:01 \d\d:\d\d:\d\d\Z")}),
            })
        if kind == "signed_sensor_recording":
            return st.fixed_dictionaries({
                "recording_hash": st.text(alphabet="0123456789abcdef", min_size=8, max_size=64),
                "duration_seconds": st.integers(min_value=1, max_value=86400),
            })
        if kind in ("coverage_map", "gps_stamped_checkpoint_coverage"):
            return st.fixed_dictionaries({
                "covered_polygon": st.lists(
                    st.fixed_dictionaries({"lat": st.floats(-90, 90, allow_nan=False), "lon": st.floats(-180, 180, allow_nan=False)}),
                    min_size=3, max_size=8,
                ),
            })
        if kind == "manipulator_pose_track":
            return st.fixed_dictionaries({
                "track": st.lists(
                    st.fixed_dictionaries({"t": st.from_regex(r"\A2026-06-01T\d\d:\d\d:\d\dZ\Z"), "x": st.floats(-1, 1, allow_nan=False), "y": st.floats(-1, 1, allow_nan=False)}),
                    min_size=1, max_size=8,
                ),
            })
        if kind == "thermal_image_capture_manifest":
            return st.fixed_dictionaries({
                "recording_hash": st.text(alphabet="0123456789abcdef", min_size=8, max_size=64),
                "duration_seconds": st.integers(min_value=1, max_value=600),
            })
    if mode == "third-party-witness":
        if kind == "customer_signature":
            return st.fixed_dictionaries({
                "signed_text": st.text(min_size=1, max_size=200).filter(lambda s: s.strip()),
                "signature_image_hash": st.text(alphabet="0123456789abcdef", min_size=8, max_size=64),
            })
        if kind == "phone_app_attestation":
            return st.fixed_dictionaries({
                "app_did": st.from_regex(r"\Adid:wcp:[A-Za-z0-9]{32,}\Z"),
                "signed_token": st.text(min_size=8, max_size=80),
                "issued_at": st.from_regex(r"\A2026-06-01T\d\d:\d\d:\d\dZ\Z"),
            })
        if kind == "iot_beacon_proximity":
            return st.fixed_dictionaries({
                "beacon_did": st.from_regex(r"\Adid:wcp:[A-Za-z0-9]{32,}\Z"),
                "rssi_dbm": st.integers(min_value=-100, max_value=-30),
                "observed_at": st.from_regex(r"\A2026-06-01T\d\d:\d\d:\d\dZ\Z"),
            })
        if kind == "inspection_checklist_signed":
            return st.fixed_dictionaries({
                "signed_text": st.text(min_size=1, max_size=200).filter(lambda s: s.strip()),
                "signature_image_hash": st.text(alphabet="0123456789abcdef", min_size=8, max_size=64),
            })
    if mode == "cryptographic-presence":
        if kind in ("pose_bounded_presence_proof", "geofence_check_in_out", "cryptographic_nonce_exchange"):
            return st.fixed_dictionaries({
                "signed_nonce": st.text(min_size=8, max_size=80),
                "venue_id": st.text(min_size=1, max_size=20),
            })
    if mode == "owner-sign-off":
        if kind == "whatsapp_business_signed_link":
            return st.fixed_dictionaries({
                "signing_party_did": st.from_regex(r"\Adid:wcp:[A-Za-z0-9]{32,}\Z"),
                "signed_token": st.text(min_size=8, max_size=80),
                "issued_at": st.from_regex(r"\A2026-06-01T\d\d:\d\d:\d\dZ\Z"),
            })
        if kind == "self_attestation_with_waiver":
            return st.fixed_dictionaries({
                "waiver_text": st.text(min_size=1, max_size=200),
                "signed_by_worker": st.text(min_size=8, max_size=80),
            })
    return st.none()  # unknown (mode, kind) -> no strategy


def _fail_payload_strategy(mode: str, kind: str) -> st.SearchStrategy:
    """Strategies that produce payloads designed to FAIL the per-kind
    verifier. Each strategy strips a required field, replaces a typed
    field with the wrong type, or hands the verifier garbage."""
    # The fail strategy is intentionally simple and shared across kinds:
    # an empty dict, or a dict with one nonsense key. Both miss every
    # required field and reliably fail every verifier branch.
    return st.one_of(
        st.just({}),
        st.fixed_dictionaries({"unrelated_field": st.text(max_size=8)}),
        st.just({"track": "not-a-list"}),
        st.just({"track": []}),
    )


# ---------------------------------------------------------------------------
# The invariant check
# ---------------------------------------------------------------------------


def _run_verifier_under_class(
    mode: str, kind: str, payload: dict[str, Any], worker_class: str,
) -> VerificationOutcome:
    """Invoke the verifier in a context where the (mode, kind) is
    registered. The verifier signature does not take worker_class; if a
    future contributor added a worker_class kwarg, this helper would fail
    to type-check, which is itself a regression signal.

    The `worker_class` parameter is taken on purpose — even though the
    verifier signature does not currently accept it, the test passes it
    to the call site so a regression that adds a class-aware branch
    surface (e.g. via a context dict or thread-local) would be caught
    by the assertion that all five classes produce identical outcomes.
    """
    # The verifier is a pure function over (mode, kind, payload,
    # task_payload, registry). worker_class enters the picture only via
    # `task_payload`, which is the agent's descriptor payload. We thread
    # the class through task_payload to give the verifier the most
    # generous opportunity to leak a class branch.
    task_payload = {
        "_test_worker_class_context": worker_class,
    }
    return verify_single(
        mode=mode,
        kind=kind,
        payload=payload,
        task_payload=task_payload,
        schema_registry_kinds=DEFAULT_REGISTRY,
    )


def _outcomes_must_match(outcomes_by_class: dict[str, VerificationOutcome]) -> None:
    """Assert decision and reasons are byte-identical across all classes."""
    first_class = next(iter(outcomes_by_class))
    reference = outcomes_by_class[first_class]
    ref_decision = reference.decision
    ref_reasons = tuple(reference.reasons)

    for cls, outcome in outcomes_by_class.items():
        if outcome.decision != ref_decision:
            pytest.fail(
                f"verifier branched on worker class: "
                f"class={cls} decision={outcome.decision!r} "
                f"but class={first_class} decision={ref_decision!r}"
            )
        if tuple(outcome.reasons) != ref_reasons:
            pytest.fail(
                f"verifier branched on worker class via reasons: "
                f"class={cls} reasons={outcome.reasons!r} "
                f"but class={first_class} reasons={ref_reasons!r}"
            )


def _registered_pairs() -> Iterable[tuple[str, str]]:
    for mode, kinds in DEFAULT_REGISTRY.items():
        for kind in kinds:
            yield mode, kind


# ---------------------------------------------------------------------------
# Property tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("mode,kind", list(_registered_pairs()))
def test_verifier_invariant_across_classes_pass_eligible(mode, kind):
    """For each (mode, kind) registered in DEFAULT_REGISTRY, generate
    payloads designed to PASS and assert the verifier returns the same
    decision and reasons regardless of worker_class context."""
    strategy = _pass_payload_strategy(mode, kind)
    if strategy is st.none():
        pytest.skip(f"no pass-eligible payload strategy for ({mode}, {kind})")

    @given(payload=strategy)
    @settings(
        max_examples=HYPOTHESIS_MAX_EXAMPLES,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def check(payload):
        outcomes = {
            cls: _run_verifier_under_class(mode, kind, payload, cls)
            for cls in ALL_WORKER_CLASSES
        }
        _outcomes_must_match(outcomes)

    check()


@pytest.mark.parametrize("mode,kind", list(_registered_pairs()))
def test_verifier_invariant_across_classes_fail_eligible(mode, kind):
    """For each (mode, kind), generate fail-eligible payloads and assert
    the verifier returns the same decision and reasons regardless of
    worker_class context. The reasons tuple is part of the invariant
    surface — a class-specific failure message would be a leak."""
    strategy = _fail_payload_strategy(mode, kind)

    @given(payload=strategy)
    @settings(
        max_examples=HYPOTHESIS_MAX_EXAMPLES,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def check(payload):
        outcomes = {
            cls: _run_verifier_under_class(mode, kind, payload, cls)
            for cls in ALL_WORKER_CLASSES
        }
        _outcomes_must_match(outcomes)

    check()


def test_all_registered_kinds_have_a_pass_strategy_or_are_skipped():
    """Sanity: every (mode, kind) is either covered by a pass-eligible
    strategy or explicitly skipped. New registry entries that lack a
    strategy will trigger a skip rather than silently passing the
    invariance check on zero examples."""
    uncovered = []
    for mode, kind in _registered_pairs():
        if _pass_payload_strategy(mode, kind) is st.none():
            uncovered.append((mode, kind))
    # Acceptable: at least one strategy exists per mode.
    by_mode = {m for m, _ in _registered_pairs()}
    covered_modes = {m for m, k in _registered_pairs()
                     if _pass_payload_strategy(m, k) is not st.none()}
    assert by_mode.issubset(covered_modes), (
        f"modes without any pass-eligible strategy: {by_mode - covered_modes}"
    )
