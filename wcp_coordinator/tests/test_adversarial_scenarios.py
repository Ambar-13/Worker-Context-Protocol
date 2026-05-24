"""
Lifecycle-layer adversarial scenarios from PLAN.md Section 7 / spec/d4-verification.md.

11 lifecycle scenarios at v0.955 (the original v0.95 set of 13 collapsed
to 11 when settlement was removed; the two settlement-dispute scenarios
no longer apply because settlement is no longer a protocol concern).

8 cryptographic-attack scenarios (nonce replay, cross-session nonce
isolation, key revocation, acceptance attestation canonicalization, and
signature-forgery sanity) live in test_adversarial_crypto.py.

Together: 19 adversarial scenarios across the lifecycle and cryptographic
surfaces. Each scenario verifies the spec response under hostile inputs.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from wcp_coordinator.tests.conftest import (
    Identity,
    make_acceptance,
    make_capability,
    make_evidence,
    make_task,
)


def _pub(services, identity, principal, cls="human"):
    caps, _, _ = services
    cap = make_capability(
        worker_id=identity.did, principal_id=principal.did, worker_class=cls
    )
    caps.upsert_capabilities(
        worker_id=identity.did, capabilities=cap, principal_id=principal.did
    )


def test_scenario1_fabricated_gps_witness_alone_insufficient(
    services, worker_identity, principal_identity, agent_identity
):
    """Single sensor-witness alone insufficient for paid task; M-of-N requires non-sensor."""
    _, tasks, _ = services
    _pub(services, worker_identity, principal_identity, "human")

    t = make_task(
        agent_did=agent_identity.did,
        attestation_modes=["sensor-witness", "third-party-witness"],
        attestation_kinds={
            "sensor-witness": ["gps_track"],
            "third-party-witness": ["customer_signature"],
        },
        M=2, N=2,
    )
    tasks.post(task=t, expiry="2026-12-31T23:59:00Z")
    eta = "2026-06-01T10:00:00Z"
    cr = tasks.claim(
        task_id=t["task_id"], worker_id=worker_identity.did, eta=eta,
        acceptance_attestation=make_acceptance(worker_identity, t["task_id"], eta=eta),
    )
    tasks.execute_open(claim_id=cr["claim_id"])
    ev = make_evidence(
        worker_identity, cr["claim_id"], "sensor-witness", "gps_track",
        {"track": [{"t": "2026-06-01T10:00:00Z", "x": 0, "y": 0}]},
    )
    r = tasks.attest(claim_id=cr["claim_id"], attestations=[ev])
    # Only 1 of 2 modes provided; M-of-N (2-of-2) fails.
    assert r["verifier_decision"] in ("fail", "review")


def test_scenario2_fabricated_photo_alone_insufficient(
    services, worker_identity, principal_identity, agent_identity
):
    _, tasks, _ = services
    _pub(services, worker_identity, principal_identity, "human")
    t = make_task(
        agent_did=agent_identity.did,
        attestation_modes=["sensor-witness", "third-party-witness"],
        attestation_kinds={
            "sensor-witness": ["photo_with_exif"],
            "third-party-witness": ["customer_signature"],
        },
        M=2, N=2,
    )
    tasks.post(task=t, expiry="2026-12-31T23:59:00Z")
    eta = "2026-06-01T10:00:00Z"
    cr = tasks.claim(
        task_id=t["task_id"], worker_id=worker_identity.did, eta=eta,
        acceptance_attestation=make_acceptance(worker_identity, t["task_id"], eta=eta),
    )
    tasks.execute_open(claim_id=cr["claim_id"])
    ev = make_evidence(
        worker_identity, cr["claim_id"], "sensor-witness", "photo_with_exif",
        {"photo_hash": "abc", "exif": {"datetime": "2026-06-01T10:30:00Z"}},
    )
    r = tasks.attest(claim_id=cr["claim_id"], attestations=[ev])
    assert r["verifier_decision"] in ("fail", "review")


def test_scenario3_self_dealing_blocked_without_third_party(
    services, worker_identity, agent_identity
):
    """Owner of robot is also the agent: tasks/claim rejects when no third-party-witness."""
    _, tasks, _ = services
    # Worker.principal == agent.posted_by (self-dealing).
    _pub(services, worker_identity, agent_identity, "human")  # principal = agent_identity
    t = make_task(
        agent_did=agent_identity.did,
        attestation_modes=["sensor-witness"],
        attestation_kinds={"sensor-witness": ["gps_track"]},
        M=1, N=1,
    )
    tasks.post(task=t, expiry="2026-12-31T23:59:00Z")
    eta = "2026-06-01T10:00:00Z"
    with pytest.raises(ValueError) as exc:
        tasks.claim(
            task_id=t["task_id"], worker_id=worker_identity.did, eta=eta,
            acceptance_attestation=make_acceptance(worker_identity, t["task_id"], eta=eta),
        )
    assert "POLICY_VIOLATION" in str(exc.value)


def test_scenario4_first_claim_wins(
    services, principal_identity, agent_identity
):
    """Scenario 4 covered in test_lifecycle::test_preempted_second_claim."""
    pass


def test_scenario5_heartbeat_timeout_promotes_supervising(
    db, services, worker_identity, principal_identity, agent_identity
):
    _, tasks, _ = services
    _pub(services, worker_identity, principal_identity, "human")
    t = make_task(agent_did=agent_identity.did, worker_class_filter=["human"])
    tasks.post(task=t, expiry="2026-12-31T23:59:00Z")
    eta = "2026-06-01T10:00:00Z"
    cr = tasks.claim(
        task_id=t["task_id"], worker_id=worker_identity.did, eta=eta,
        acceptance_attestation=make_acceptance(worker_identity, t["task_id"], eta=eta),
    )
    tasks.execute_open(claim_id=cr["claim_id"])

    # Backdate heartbeat by 60 seconds (> 45s threshold).
    from wcp_coordinator.models import WcpClaim
    claim = db.get(WcpClaim, cr["claim_id"])
    claim.last_heartbeat_at = datetime.now(timezone.utc) - timedelta(seconds=60)
    db.flush()

    promoted = tasks.check_heartbeats()
    assert cr["claim_id"] in promoted


def test_scenario8_invalid_attestation_requirement_M_gt_N(
    services, agent_identity
):
    _, tasks, _ = services
    t = make_task(agent_did=agent_identity.did, M=5, N=2)
    with pytest.raises(ValueError) as exc:
        tasks.post(task=t, expiry="2026-12-31T23:59:00Z")
    assert "INVALID_ATTESTATION_REQUIREMENT" in str(exc.value)


def test_scenario8_unknown_kind_rejected(services, agent_identity):
    _, tasks, _ = services
    t = make_task(
        agent_did=agent_identity.did,
        attestation_kinds={
            "cryptographic-presence": ["geofence_check_in_out"],
            "owner-sign-off": ["nonexistent_kind"],
        },
    )
    with pytest.raises(ValueError) as exc:
        tasks.post(task=t, expiry="2026-12-31T23:59:00Z")
    assert "INVALID_ATTESTATION_REQUIREMENT" in str(exc.value)


def test_scenario9_audit_trail_complete(
    services, worker_identity, principal_identity, agent_identity
):
    """Every state transition emits a signed audit chain entry."""
    _, tasks, audit = services
    _pub(services, worker_identity, principal_identity, "human")
    t = make_task(agent_did=agent_identity.did, worker_class_filter=["human"])
    tasks.post(task=t, expiry="2026-12-31T23:59:00Z")
    eta = "2026-06-01T10:00:00Z"
    cr = tasks.claim(
        task_id=t["task_id"], worker_id=worker_identity.did, eta=eta,
        acceptance_attestation=make_acceptance(worker_identity, t["task_id"], eta=eta),
    )
    tasks.execute_open(claim_id=cr["claim_id"])
    assert audit.verify_chain(cr["claim_id"])


def test_scenario11_out_of_scope_task_class_refused(services, agent_identity):
    _, tasks, _ = services
    t = make_task(agent_did=agent_identity.did, descriptor_type="medical")
    with pytest.raises(ValueError) as exc:
        tasks.post(task=t, expiry="2026-12-31T23:59:00Z")
    assert "OUT_OF_SCOPE_TASK_CLASS" in str(exc.value)


def test_scenario12_supervision_handoff_preserves_attestation_requirement(
    services, worker_identity, principal_identity, agent_identity
):
    """The agent's contract does not move under the worker's feet."""
    _, tasks, _ = services
    _pub(services, worker_identity, principal_identity, "teleoperated_robot")
    t = make_task(
        agent_did=agent_identity.did, worker_class_filter=["teleoperated_robot"]
    )
    tasks.post(task=t, expiry="2026-12-31T23:59:00Z")
    eta = "2026-06-01T10:00:00Z"
    cr = tasks.claim(
        task_id=t["task_id"], worker_id=worker_identity.did, eta=eta,
        acceptance_attestation=make_acceptance(worker_identity, t["task_id"], eta=eta),
    )
    tasks.execute_open(claim_id=cr["claim_id"])
    res = tasks.supervise(
        claim_id=cr["claim_id"],
        handoff_reason="uncertainty",
        state_snapshot={"pose": [1, 2]},
        urgency="high",
    )
    assert res["supervisor_id"]
    # The task is still subject to the original attestation_requirement.
    from wcp_coordinator.models import WcpTask
    t_db = next(iter([row for row in [tasks._db.get(WcpTask, t["task_id"])]]))
    assert t_db.task_json["attestation_requirement"]["modes"] == [
        "cryptographic-presence",
        "owner-sign-off",
    ]


def test_scenario13_subcontract_forbidden_at_v01(services, agent_identity):
    _, tasks, _ = services
    t = make_task(agent_did=agent_identity.did)
    t["x-subcontract-allowed"] = True
    with pytest.raises(ValueError) as exc:
        tasks.post(task=t, expiry="2026-12-31T23:59:00Z")
    assert "SUBCONTRACT_FORBIDDEN" in str(exc.value)
