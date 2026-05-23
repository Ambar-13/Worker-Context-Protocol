"""Unit tests for wcp_worker.attestation_collector."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from wcp_worker.attestation_collector import AttestationCollector
from wcp_worker.identity import WorkerIdentity


def test_indoor_pose_track_evidence(tmp_path: Path) -> None:
    ident = WorkerIdentity.load_or_generate(tmp_path / "key")
    c = AttestationCollector(ident)
    track = [
        {"t": "2026-06-01T10:00:00Z", "x": 0.0, "y": 0.0},
        {"t": "2026-06-01T10:00:15Z", "x": 1.0, "y": 1.0},
    ]
    ev = c.indoor_pose_track("c1", track)
    assert ev["mode"] == "sensor-witness"
    assert ev["kind"] == "indoor_pose_track"
    assert ev["worker_id"] == ident.did
    assert ev["sig"].startswith("ed25519:")
    assert ev["payload"]["track"] == track


def test_pose_bounded_presence_evidence(tmp_path: Path) -> None:
    ident = WorkerIdentity.load_or_generate(tmp_path / "key")
    c = AttestationCollector(ident)
    t1 = datetime(2026, 6, 1, 2, 0, tzinfo=timezone.utc)
    t2 = t1 + timedelta(minutes=45)
    ev = c.pose_bounded_presence_proof(
        "c1",
        check_in_at=t1,
        check_out_at=t2,
        region={"polygon": [[0, 0], [10, 0], [10, 10], [0, 10]]},
    )
    assert ev["mode"] == "cryptographic-presence"
    assert ev["payload"]["check_in_at"].startswith("2026-06-01")


def test_photo_evidence_carries_hash_not_bytes(tmp_path: Path) -> None:
    ident = WorkerIdentity.load_or_generate(tmp_path / "key")
    c = AttestationCollector(ident)
    ev = c.photo_with_exif(
        "c1",
        photo_bytes=b"PHOTO-DATA",
        exif={"datetime": "2026-06-01T10:00:00Z"},
    )
    assert "photo_hash" in ev["payload"]
    assert "photo_bytes" not in ev["payload"]
