"""Builds and publishes the robot's CapabilityDescriptor.

Robot-class capabilities populate the `class_extension.kinematics`,
`payload`, `end_effectors`, and `environment` fields per spec/0.1.md
Section 4. The required block remains identical to the human case.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .identity import WorkerIdentity
from .rpc_client import RpcClient


class CapabilityPublisher:
    def __init__(
        self,
        identity: WorkerIdentity,
        rpc: RpcClient,
        *,
        principal_id: str,
        venue_id: str,
        map_id: str,
        kinematics: dict[str, Any],
        payload: dict[str, Any],
        end_effectors: list[dict[str, Any]],
        environment: dict[str, Any],
    ) -> None:
        self._identity = identity
        self._rpc = rpc
        self._principal_id = principal_id
        self._venue_id = venue_id
        self._map_id = map_id
        self._kinematics = kinematics
        self._payload_specs = payload
        self._end_effectors = end_effectors
        self._environment = environment

    def build_descriptor(self) -> dict[str, Any]:
        return {
            "schema_version": "wcp/0.1",
            "worker_id": self._identity.did,
            "principal_id": self._principal_id,
            "class": "autonomous_robot",
            "required": {
                "current_location": {
                    "venue_id": self._venue_id,
                    "map_id": self._map_id,
                },
                "available_windows": [
                    {"rrule": "FREQ=DAILY", "timezone": "Asia/Singapore"}
                ],
                "attestation_methods_supported": [
                    "sensor-witness",
                    "third-party-witness",
                    "cryptographic-presence",
                ],
                "certifications": [],
                "policy_windows": [{"type": "geographic", "scope": "Singapore"}],
                "attestation_keys": [
                    {
                        "kty": "OKP",
                        "crv": "Ed25519",
                        "x": self._identity.public_key_b64url,
                    }
                ],
                "as_of": datetime.now(timezone.utc).isoformat(),
            },
            "class_extension": {
                "kinematics": self._kinematics,
                "payload": self._payload_specs,
                "end_effectors": self._end_effectors,
                "environment": self._environment,
            },
        }

    async def publish(self) -> None:
        descriptor = self.build_descriptor()
        await self._rpc.call(
            "capabilities/list",
            {"worker_id": self._identity.did, "capabilities": descriptor},
        )
