"""Session-level helpers that do not require a live RPC connection."""
from __future__ import annotations

from wcp_sdk.identity import WorkerIdentity, verify_signature
from wcp_sdk.canonical import canonical_json_bytes
from wcp_sdk.session import WorkerSession
from wcp_sdk.types import AttestationMode


def test_build_evidence_produces_verifiable_signature():
    ident = WorkerIdentity.generate()
    sess = WorkerSession("wss://example/wcp/ws", ident)
    ev = sess.build_evidence(
        claim_id="c1",
        mode=AttestationMode.SENSOR_WITNESS,
        kind="gps_track",
        payload={"track": [{"t": "2026-06-01T10:00:00Z", "x": 0, "y": 0}]},
    )
    assert ev.sig.startswith("ed25519:")
    canonical = {
        "mode": "sensor-witness",
        "kind": "gps_track",
        "payload_hash": ev.payload_hash,
        "worker_id": ident.did,
        "claim_id": "c1",
        "collected_at": ev.collected_at,
    }
    verify_signature(ident.did, canonical_json_bytes(canonical), ev.sig)


def test_build_evidence_includes_schema_version():
    ident = WorkerIdentity.generate()
    sess = WorkerSession("wss://example/wcp/ws", ident)
    ev = sess.build_evidence(
        claim_id="c1",
        mode=AttestationMode.THIRD_PARTY_WITNESS,
        kind="customer_signature",
        payload={"signed_text": "ok", "signature_image_hash": "abc"},
    )
    assert ev.to_dict()["schema_version"] == "wcp/1.0-rc1"
