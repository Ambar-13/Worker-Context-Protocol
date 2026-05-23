"""Collects attestation evidence on the robot worker side.

Robot evidence is sensor-rooted: indoor pose tracks from odometry, photos
from onboard cameras, presence proofs over duration. The verifier on the
coordinator side discriminates by (mode, kind) only, so the robot-side
collector and the human-side collector emit evidence of identical shape
through the SAME schema.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from .identity import WorkerIdentity, canonical_json


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class AttestationCollector:
    def __init__(self, identity: WorkerIdentity) -> None:
        self._identity = identity

    def indoor_pose_track(
        self, claim_id: str, track: list[dict[str, Any]]
    ) -> dict[str, Any]:
        payload = {"track": track}
        return self._wrap("sensor-witness", "indoor_pose_track", payload, claim_id)

    def signed_sensor_recording(
        self, claim_id: str, *, recording_bytes: bytes, duration_seconds: int
    ) -> dict[str, Any]:
        payload = {
            "recording_hash": _sha256_hex(recording_bytes),
            "duration_seconds": duration_seconds,
        }
        return self._wrap("sensor-witness", "signed_sensor_recording", payload, claim_id)

    def photo_with_exif(
        self, claim_id: str, *, photo_bytes: bytes, exif: dict[str, Any]
    ) -> dict[str, Any]:
        payload = {"photo_hash": _sha256_hex(photo_bytes), "exif": exif}
        return self._wrap("sensor-witness", "photo_with_exif", payload, claim_id)

    def pose_bounded_presence_proof(
        self,
        claim_id: str,
        *,
        check_in_at: datetime,
        check_out_at: datetime,
        region: dict[str, Any],
    ) -> dict[str, Any]:
        payload = {
            "check_in_at": check_in_at.isoformat(),
            "check_out_at": check_out_at.isoformat(),
            "region": region,
        }
        return self._wrap(
            "cryptographic-presence",
            "pose_bounded_presence_proof",
            payload,
            claim_id,
        )

    def customer_signature(
        self, claim_id: str, *, signed_text: str, signature_image_bytes: bytes
    ) -> dict[str, Any]:
        payload = {
            "signed_text": signed_text,
            "signature_image_hash": _sha256_hex(signature_image_bytes),
        }
        return self._wrap(
            "third-party-witness", "customer_signature", payload, claim_id
        )

    def _wrap(
        self,
        mode: str,
        kind: str,
        payload: dict[str, Any],
        claim_id: str,
    ) -> dict[str, Any]:
        collected_at = datetime.now(timezone.utc).isoformat()
        payload_hash = _sha256_hex(canonical_json(payload))
        canonical = {
            "mode": mode,
            "kind": kind,
            "payload_hash": payload_hash,
            "worker_id": self._identity.did,
            "claim_id": claim_id,
            "collected_at": collected_at,
        }
        sig = self._identity.sign(canonical)
        return {
            "schema_version": "wcp/0.1",
            "mode": mode,
            "kind": kind,
            "payload": payload,
            "payload_hash": payload_hash,
            "sig": sig,
            "worker_id": self._identity.did,
            "claim_id": claim_id,
            "collected_at": collected_at,
        }
