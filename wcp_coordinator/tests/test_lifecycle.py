"""End-to-end lifecycle tests: post -> claim -> execute -> attest -> settle.

Each test exercises a full RPC round-trip against in-memory SQLite.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from wcp_coordinator.tests.conftest import (
    make_acceptance,
    make_capability,
    make_evidence,
    make_task,
)


def _publish_worker(services, worker_identity, principal_identity, worker_class="human"):
    caps, tasks, _ = services
    cap = make_capability(
        worker_id=worker_identity.did,
        principal_id=principal_identity.did,
        worker_class=worker_class,
    )
    caps.upsert_capabilities(
        worker_id=worker_identity.did,
        capabilities=cap,
        principal_id=principal_identity.did,
    )


def test_happy_path_human_scheduled_presence(
    services, worker_identity, principal_identity, agent_identity
):
    caps, tasks, audit = services
    _publish_worker(services, worker_identity, principal_identity, "human")

    # Post.
    t = make_task(agent_did=agent_identity.did, worker_class_filter=["human"])
    posted = tasks.post(
        task=t,
        expiry="2026-12-31T23:59:00Z",
    )
    assert posted["eligible_workers_count"] >= 1

    # Claim.
    eta = "2026-06-01T10:00:00Z"
    acceptance = make_acceptance(worker_identity, t["task_id"], eta=eta)
    claim_result = tasks.claim(
        task_id=t["task_id"],
        worker_id=worker_identity.did,
        eta=eta,
        acceptance_attestation=acceptance,
    )
    assert claim_result["accepted"] is True

    # Execute.
    open_res = tasks.execute_open(claim_id=claim_result["claim_id"])
    assert open_res["state"] == "executing"

    # Attest: 2-of-2 (cryptographic-presence + owner-sign-off).
    ev1 = make_evidence(
        worker_identity,
        claim_result["claim_id"],
        "cryptographic-presence",
        "geofence_check_in_out",
        {
            "check_in_at": "2026-06-01T10:00:00+00:00",
            "check_out_at": "2026-06-01T10:50:00+00:00",
            "region": {"polygon": [[0, 0], [10, 0], [10, 10], [0, 10]]},
        },
    )
    ev2 = make_evidence(
        worker_identity,
        claim_result["claim_id"],
        "owner-sign-off",
        "whatsapp_business_signed_link",
        {
            "signing_party_did": "did:wcp:customer",
            "signed_token": "tok-xyz",
            "issued_at": "2026-06-01T10:50:00+00:00",
        },
    )
    attest_res = tasks.attest(
        claim_id=claim_result["claim_id"], attestations=[ev1, ev2]
    )
    assert attest_res["verifier_decision"] == "pass", attest_res

    # v0.955: verifier=pass transitions the task to COMPLETED and emits a
    # task_completed audit entry. No tasks/settle RPC; settlement happens at
    # a layer above WCP that subscribes to the audit chain.

    # Audit chain integrity.
    assert audit.verify_chain(claim_result["claim_id"])


def test_happy_path_robot_transport(
    services, worker_identity, principal_identity, agent_identity
):
    caps, tasks, audit = services
    _publish_worker(services, worker_identity, principal_identity, "autonomous_robot")

    t = make_task(
        agent_did=agent_identity.did,
        descriptor_type="transport",
        descriptor_payload={
            "pickup": {"venue_id": "v1", "map_id": "m1", "pose": [0, 0, 0]},
            "dropoff": {"venue_id": "v1", "map_id": "m1", "pose": [5, 5, 0]},
            "payload_description": "demo box",
        },
        attestation_modes=["sensor-witness", "third-party-witness"],
        attestation_kinds={
            "sensor-witness": ["indoor_pose_track"],
            "third-party-witness": ["customer_signature"],
        },
        worker_class_filter=["autonomous_robot"],
    )
    posted = tasks.post(task=t, expiry="2026-12-31T23:59:00Z")
    eta = "2026-06-01T10:00:00Z"
    acceptance = make_acceptance(worker_identity, t["task_id"], eta=eta)
    cr = tasks.claim(
        task_id=t["task_id"],
        worker_id=worker_identity.did,
        eta=eta,
        acceptance_attestation=acceptance,
    )
    tasks.execute_open(claim_id=cr["claim_id"])

    ev1 = make_evidence(
        worker_identity,
        cr["claim_id"],
        "sensor-witness",
        "indoor_pose_track",
        {"track": [{"t": "2026-06-01T10:00:00Z", "x": 0, "y": 0}]},
    )
    ev2 = make_evidence(
        worker_identity,
        cr["claim_id"],
        "third-party-witness",
        "customer_signature",
        {"signed_text": "Delivered.", "signature_image_hash": "abc"},
    )
    r = tasks.attest(claim_id=cr["claim_id"], attestations=[ev1, ev2])
    assert r["verifier_decision"] == "pass"
    # v0.955: no tasks/settle; the COMPLETED transition is implicit on pass.


def test_preempted_second_claim(
    db, services, principal_identity, agent_identity
):
    """Scenario 4: two workers claim the same task simultaneously."""
    from wcp_coordinator.tasks_service import TaskPreempted
    from wcp_coordinator.tests.conftest import Identity

    caps, tasks, _ = services
    w1 = Identity("w1")
    w2 = Identity("w2")
    _publish_worker(services, w1, principal_identity, "human")
    _publish_worker(services, w2, principal_identity, "human")

    t = make_task(agent_did=agent_identity.did, worker_class_filter=["human"])
    tasks.post(task=t, expiry="2026-12-31T23:59:00Z")

    eta = "2026-06-01T10:00:00Z"
    a1 = make_acceptance(w1, t["task_id"], eta=eta)
    a2 = make_acceptance(w2, t["task_id"], eta=eta)
    tasks.claim(
        task_id=t["task_id"], worker_id=w1.did, eta=eta, acceptance_attestation=a1
    )
    with pytest.raises(TaskPreempted):
        tasks.claim(
            task_id=t["task_id"], worker_id=w2.did, eta=eta, acceptance_attestation=a2
        )
