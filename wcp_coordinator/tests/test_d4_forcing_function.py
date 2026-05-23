"""
D4 forcing function in code: the same nine RPCs handle all six cells
(3 descriptors x 2 worker classes) without modification.

The asymmetry between cells lives only in `descriptor_payload` and
`attestation_requirement.evidence_schema`.
"""
from __future__ import annotations

import pytest

from wcp_coordinator.tests.conftest import (
    Identity,
    make_acceptance,
    make_capability,
    make_evidence,
    make_task,
)


def _pub(services, identity, principal, cls):
    caps, _, _ = services
    cap = make_capability(
        worker_id=identity.did, principal_id=principal.did, worker_class=cls
    )
    caps.upsert_capabilities(
        worker_id=identity.did, capabilities=cap, principal_id=principal.did
    )


D4_CELLS = [
    # (cell_name, worker_class, descriptor_type, modes, kinds, ev_specs)
    (
        "A1-transport-robot",
        "autonomous_robot",
        "transport",
        ["sensor-witness", "third-party-witness"],
        {"sensor-witness": ["indoor_pose_track"], "third-party-witness": ["customer_signature"]},
        [
            ("sensor-witness", "indoor_pose_track",
             {"track": [{"t": "2026-06-01T10:00:00Z", "x": 0, "y": 0}]}),
            ("third-party-witness", "customer_signature",
             {"signed_text": "Delivered", "signature_image_hash": "abc"}),
        ],
    ),
    (
        "A2-transport-human",
        "human",
        "transport",
        ["sensor-witness", "third-party-witness"],
        {"sensor-witness": ["gps_track"], "third-party-witness": ["customer_signature"]},
        [
            ("sensor-witness", "gps_track",
             {"track": [{"t": "2026-06-01T10:00:00Z", "x": 0, "y": 0}]}),
            ("third-party-witness", "customer_signature",
             {"signed_text": "Delivered", "signature_image_hash": "abc"}),
        ],
    ),
    (
        "B1-presence-robot",
        "autonomous_robot",
        "scheduled_presence",
        ["cryptographic-presence", "sensor-witness"],
        {"cryptographic-presence": ["pose_bounded_presence_proof"],
         "sensor-witness": ["photo_with_exif"]},
        [
            ("cryptographic-presence", "pose_bounded_presence_proof",
             {"check_in_at": "2026-06-01T02:00:00+00:00",
              "check_out_at": "2026-06-01T02:45:00+00:00",
              "region": {"polygon": [[0, 0], [10, 0], [10, 10], [0, 10]]}}),
            ("sensor-witness", "photo_with_exif",
             {"photo_hash": "abc", "exif": {"datetime": "2026-06-01T02:30:00Z"}}),
        ],
    ),
    (
        "B2-presence-human",
        "human",
        "scheduled_presence",
        ["cryptographic-presence", "owner-sign-off"],
        {"cryptographic-presence": ["geofence_check_in_out"],
         "owner-sign-off": ["whatsapp_business_signed_link"]},
        [
            ("cryptographic-presence", "geofence_check_in_out",
             {"check_in_at": "2026-06-01T10:00:00+00:00",
              "check_out_at": "2026-06-01T10:50:00+00:00",
              "region": {"polygon": [[0, 0], [10, 0], [10, 10], [0, 10]]}}),
            ("owner-sign-off", "whatsapp_business_signed_link",
             {"signing_party_did": "did:wcp:customer", "signed_token": "t",
              "issued_at": "2026-06-01T10:50:00Z"}),
        ],
    ),
    (
        "C1-observe-robot",
        "autonomous_robot",
        "observe_and_report",
        ["sensor-witness"],
        {"sensor-witness": ["signed_sensor_recording", "coverage_map"]},
        [
            ("sensor-witness", "signed_sensor_recording",
             {"recording_hash": "h1", "duration_seconds": 300}),
        ],
    ),
    (
        "C2-observe-human",
        "human",
        "observe_and_report",
        ["sensor-witness"],
        {"sensor-witness": ["photo_with_exif", "gps_stamped_checkpoint_coverage"]},
        [
            ("sensor-witness", "photo_with_exif",
             {"photo_hash": "h2", "exif": {"datetime": "2026-06-01T11:00:00Z"}}),
        ],
    ),
]


@pytest.mark.parametrize(
    "cell_name,worker_class,descriptor_type,modes,kinds,evidence_specs",
    D4_CELLS,
)
def test_d4_cell_round_trips(
    services, principal_identity, agent_identity,
    cell_name, worker_class, descriptor_type, modes, kinds, evidence_specs,
):
    """For each of the 6 D4 cells, post -> claim -> execute -> attest -> settle
    using the EXACT SAME 9 RPCs. No new RPC. No new parameter."""
    _, tasks, audit = services
    w = Identity(cell_name)
    _pub(services, w, principal_identity, worker_class)

    t = make_task(
        agent_did=agent_identity.did,
        descriptor_type=descriptor_type,
        attestation_modes=modes,
        attestation_kinds=kinds,
        M=len(modes), N=len(modes),  # all-of-N
        worker_class_filter=[worker_class],
    )
    tasks.post(task=t, bond_ref=f"pi_{cell_name}", expiry="2026-12-31T23:59:00Z")
    eta = "2026-06-01T10:00:00Z"
    cr = tasks.claim(
        task_id=t["task_id"], worker_id=w.did, eta=eta,
        acceptance_attestation=make_acceptance(w, t["task_id"], eta=eta),
    )
    tasks.execute_open(claim_id=cr["claim_id"])
    evidence = [
        make_evidence(w, cr["claim_id"], mode, kind, payload)
        for mode, kind, payload in evidence_specs
    ]
    res = tasks.attest(claim_id=cr["claim_id"], attestations=evidence)
    assert res["verifier_decision"] in ("pass", "review"), (cell_name, res)
    if res["verifier_decision"] == "pass":
        settle = tasks.settle(
            claim_id=cr["claim_id"], decision="release", amount="100.00",
            party_breakdown=[
                {"party": "did:wcp:worker-principal", "amount": "80.00"},
                {"party": "did:wcp:platform", "amount": "15.00"},
                {"party": "did:wcp:insurance-pool", "amount": "5.00"},
            ],
        )
        assert settle["state"] == "captured", cell_name
    assert audit.verify_chain(cr["claim_id"])
