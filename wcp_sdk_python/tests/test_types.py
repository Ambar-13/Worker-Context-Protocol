"""Typed-object construction and serialization tests."""
from __future__ import annotations

from wcp_sdk.session import make_task_descriptor
from wcp_sdk.types import (
    AttestationEvidence,
    AttestationMode,
    AttestationRequirement,
    CapabilityDescriptor,
    Settlement,
    SettlementSplitEntry,
    TaskDescriptor,
    WorkerClass,
)


def test_capability_descriptor_serializes_required_block():
    cap = CapabilityDescriptor(
        worker_id="did:wcp:abc",
        principal_id="did:wcp:p1",
        worker_class=WorkerClass.HUMAN,
        current_location={"venue_id": "v1", "map_id": "m1"},
        attestation_methods_supported=["sensor-witness", "third-party-witness"],
        attestation_keys=[{"kty": "OKP", "crv": "Ed25519", "x": "abc"}],
        class_extension={"skills": ["aircon"]},
    )
    out = cap.to_dict()
    assert out["schema_version"] == "wcp/1.0-rc1"
    assert out["class"] == "human"
    assert "as_of" in out["required"]
    assert out["class_extension"]["skills"] == ["aircon"]


def test_task_descriptor_round_trip_via_helper():
    td = make_task_descriptor(
        posted_by="did:wcp:agent",
        descriptor_type="scheduled_presence",
        descriptor_payload={"duration_minutes": 45},
        attestation_modes=[
            AttestationMode.CRYPTOGRAPHIC_PRESENCE,
            AttestationMode.OWNER_SIGN_OFF,
        ],
        attestation_kinds={
            "cryptographic-presence": ["geofence_check_in_out"],
            "owner-sign-off": ["whatsapp_business_signed_link"],
        },
        M=2,
        N=2,
        currency="USD",
        amount="100.00",
        escrow_provider="example-escrow",
        split=[("did:wcp:worker", 80), ("did:wcp:platform", 20)],
        worker_class_filter=[WorkerClass.HUMAN],
    )
    out = td.to_dict()
    assert out["schema_version"] == "wcp/1.0-rc1"
    assert out["descriptor_type"] == "scheduled_presence"
    assert out["attestation_requirement"]["M"] == 2
    assert out["attestation_requirement"]["N"] == 2
    assert len(out["settlement"]["split"]) == 2
    assert out["x-subcontract-allowed"] is False


def test_attestation_requirement_includes_override_authority_did():
    ar = AttestationRequirement(
        modes=[AttestationMode.SENSOR_WITNESS],
        threshold="any",
        M=1,
        N=1,
        evidence_schema=[{"mode": "sensor-witness", "kinds": ["gps_track"]}],
        override_authority="did:wcp:operator-ops",
    )
    out = ar.to_dict()
    assert out["override_authority"].startswith("did:wcp:")


def test_attestation_evidence_carries_signature_fields():
    ev = AttestationEvidence(
        mode=AttestationMode.SENSOR_WITNESS,
        kind="gps_track",
        payload={"track": []},
        payload_hash="0" * 64,
        sig="ed25519:abc",
        worker_id="did:wcp:abc",
        claim_id="c1",
        collected_at="2026-06-01T10:00:00Z",
    )
    out = ev.to_dict()
    assert out["sig"].startswith("ed25519:")
    assert out["schema_version"] == "wcp/1.0-rc1"


def test_settlement_split_entry_dict_shape():
    e = SettlementSplitEntry(party="did:wcp:worker", pct=80.0)
    out = e.to_dict()
    assert set(out) == {"party", "pct"}


def test_x_subcontract_allowed_defaults_false():
    td = make_task_descriptor(
        posted_by="did:wcp:agent",
        descriptor_type="transport",
        descriptor_payload={},
        attestation_modes=[AttestationMode.SENSOR_WITNESS],
        attestation_kinds={"sensor-witness": ["gps_track"]},
        M=1,
        N=1,
        currency="USD",
        amount="10.00",
        escrow_provider="example-escrow",
        split=[("did:wcp:worker", 100)],
    )
    assert td.to_dict()["x-subcontract-allowed"] is False
