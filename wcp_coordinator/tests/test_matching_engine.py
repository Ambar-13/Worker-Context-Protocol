"""Tests for the matching engine's structural discrimination invariants.

The matching engine reads ONLY the `required` block of a capability
descriptor plus the task's `worker_class_filter`. It MUST NOT read the
opaque `class_extension` block, and it MUST NOT branch on `agent_class`
or any other informational metadata. These tests pin those invariants
in code per Section 4 of the paper (the D4 forcing function).
"""
from __future__ import annotations

from typing import Any

from wcp_coordinator.capabilities_service import CapabilitiesService

from wcp_coordinator.tests.conftest import Identity, make_capability


def _register(caps: CapabilitiesService, ident: Identity, **overrides: Any):
    """Helper: build a capability and upsert it."""
    cap = make_capability(
        worker_id=ident.did,
        principal_id=ident.did,
        **overrides,
    )
    return caps.upsert_capabilities(
        worker_id=ident.did,
        capabilities=cap,
        principal_id=ident.did,
    )


def test_matching_returns_all_when_query_empty(db, resolver):
    """An empty capability_query plus a class filter that matches every
    worker returns every worker."""
    caps = CapabilitiesService(db, resolver)
    _register(caps, Identity("w1"))
    _register(caps, Identity("w2"))
    result = caps.matching_workers(
        capability_query={}, worker_class_filter=["human"]
    )
    assert len(result) == 2


def test_matching_filters_by_attestation_methods(db, resolver):
    """A worker that lacks a requested attestation method is filtered out."""
    caps = CapabilitiesService(db, resolver)
    w1 = Identity("w1")
    _register(
        caps,
        w1,
        # default attestation_methods_supported includes sensor-witness etc.
    )

    # Worker w2 has only owner-sign-off support.
    w2 = Identity("w2")
    cap_w2 = make_capability(worker_id=w2.did, principal_id=w2.did)
    cap_w2["required"]["attestation_methods_supported"] = ["owner-sign-off"]
    caps.upsert_capabilities(
        worker_id=w2.did,
        capabilities=cap_w2,
        principal_id=w2.did,
    )

    # Query needs sensor-witness; only w1 should match.
    result = caps.matching_workers(
        capability_query={"attestation_methods": ["sensor-witness"]},
        worker_class_filter=["human"],
    )
    dids = {r.worker_id for r in result}
    assert w1.did in dids
    assert w2.did not in dids


def test_matching_filters_by_certifications(db, resolver):
    """A worker without a requested certification is filtered out."""
    caps = CapabilitiesService(db, resolver)

    w_cert = Identity("w_cert")
    cap_cert = make_capability(worker_id=w_cert.did, principal_id=w_cert.did)
    cap_cert["required"]["certifications"] = [
        {"issuer": "vendor", "id": "THERMAL-IR-L2", "expires": "2027-12-31"}
    ]
    caps.upsert_capabilities(
        worker_id=w_cert.did,
        capabilities=cap_cert,
        principal_id=w_cert.did,
    )

    w_no_cert = Identity("w_no_cert")
    _register(caps, w_no_cert)

    result = caps.matching_workers(
        capability_query={"certifications": ["THERMAL-IR-L2"]},
        worker_class_filter=["human"],
    )
    dids = {r.worker_id for r in result}
    assert w_cert.did in dids
    assert w_no_cert.did not in dids


def test_matching_ignores_class_extension(db, resolver):
    """LOAD-BEARING: the matcher MUST NOT read class_extension.

    Two workers with identical required blocks but different
    class_extension content must both surface for any query that
    matches the required block. If a future regression makes the
    matcher branch on class_extension, this test fails.
    """
    caps = CapabilitiesService(db, resolver)

    w_a = Identity("w_a")
    cap_a = make_capability(worker_id=w_a.did, principal_id=w_a.did)
    cap_a["class_extension"] = {"badge_color": "red", "favourite_ice_cream": "rum_raisin"}
    caps.upsert_capabilities(
        worker_id=w_a.did, capabilities=cap_a, principal_id=w_a.did
    )

    w_b = Identity("w_b")
    cap_b = make_capability(worker_id=w_b.did, principal_id=w_b.did)
    cap_b["class_extension"] = {
        "badge_color": "blue",
        "kinematics": {"reach_m": 1.4, "payload_kg": 30},
    }
    caps.upsert_capabilities(
        worker_id=w_b.did, capabilities=cap_b, principal_id=w_b.did
    )

    # Same query, both should match because their REQUIRED blocks are equal.
    result = caps.matching_workers(
        capability_query={"attestation_methods": ["sensor-witness"]},
        worker_class_filter=["human"],
    )
    dids = {r.worker_id for r in result}
    assert {w_a.did, w_b.did}.issubset(dids), (
        "matcher must not discriminate by class_extension content"
    )


def test_matching_combines_class_filter_and_capability_query(db, resolver):
    """worker_class_filter and capability_query both apply (AND, not OR)."""
    caps = CapabilitiesService(db, resolver)
    w_human = Identity("w_human")
    _register(caps, w_human, worker_class="human")
    w_robot = Identity("w_robot")
    _register(caps, w_robot, worker_class="autonomous_robot")

    # Class filter limits to autonomous_robot only.
    result = caps.matching_workers(
        capability_query={"attestation_methods": ["sensor-witness"]},
        worker_class_filter=["autonomous_robot"],
    )
    dids = {r.worker_id for r in result}
    assert w_robot.did in dids
    assert w_human.did not in dids


def test_matching_returns_empty_on_no_match(db, resolver):
    """When nothing matches, return an empty list — not an error."""
    caps = CapabilitiesService(db, resolver)
    w = Identity("w")
    _register(caps, w)

    result = caps.matching_workers(
        # A method that no worker supports.
        capability_query={"attestation_methods": ["does-not-exist-method"]},
        worker_class_filter=["human"],
    )
    assert result == []
