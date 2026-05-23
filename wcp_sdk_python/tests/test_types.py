"""Typed-object construction and serialization tests.

v0.955: Settlement and SettlementSplitEntry types removed. The override_*
fields on AttestationRequirement removed. New optional fields on
TaskDescriptor: max_attestation_attempts and marketplace_ref.
"""
from __future__ import annotations

from wcp_sdk.session import make_task_descriptor
from wcp_sdk.types import (
    AttestationEvidence,
    AttestationMode,
    AttestationRequirement,
    CapabilityDescriptor,
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
    assert out["schema_version"] == "wcp/0.2"
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
        worker_class_filter=[WorkerClass.HUMAN],
        max_attestation_attempts=3,
        marketplace_ref="external-ref-001",
    )
    out = td.to_dict()
    assert out["schema_version"] == "wcp/0.2"
    assert out["descriptor_type"] == "scheduled_presence"
    assert out["attestation_requirement"]["M"] == 2
    assert out["attestation_requirement"]["N"] == 2
    assert out["max_attestation_attempts"] == 3
    assert out["marketplace_ref"] == "external-ref-001"
    assert "settlement" not in out
    assert out["x-subcontract-allowed"] is False


def test_attestation_requirement_serializes_thresholds():
    ar = AttestationRequirement(
        modes=[AttestationMode.SENSOR_WITNESS],
        threshold="any",
        M=1,
        N=1,
        evidence_schema=[{"mode": "sensor-witness", "kinds": ["gps_track"]}],
    )
    out = ar.to_dict()
    assert out["threshold"] == "any"
    assert "override_authority" not in out
    assert "override_allowed" not in out


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
    assert out["schema_version"] == "wcp/0.2"


def test_task_descriptor_omits_marketplace_ref_when_unset():
    td = make_task_descriptor(
        posted_by="did:wcp:agent",
        descriptor_type="transport",
        descriptor_payload={},
        attestation_modes=[AttestationMode.SENSOR_WITNESS],
        attestation_kinds={"sensor-witness": ["gps_track"]},
        M=1,
        N=1,
    )
    out = td.to_dict()
    assert "marketplace_ref" not in out
    assert out["max_attestation_attempts"] == 1


def test_x_subcontract_allowed_defaults_false():
    td = make_task_descriptor(
        posted_by="did:wcp:agent",
        descriptor_type="transport",
        descriptor_payload={},
        attestation_modes=[AttestationMode.SENSOR_WITNESS],
        attestation_kinds={"sensor-witness": ["gps_track"]},
        M=1,
        N=1,
    )
    assert td.to_dict()["x-subcontract-allowed"] is False
