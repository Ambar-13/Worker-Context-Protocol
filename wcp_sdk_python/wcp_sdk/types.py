"""
Typed objects mirroring spec/1.0-rc1.md.

These are Python dataclasses for ergonomic construction; they serialize to
the JSON shapes defined in spec/schemas/. The SDK does NOT enforce schema
validation on the wire (that is the coordinator's responsibility) but DOES
construct shapes that pass the schemas by default.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


SCHEMA_VERSION = "wcp/1.0-rc1"


class WorkerClass(str, Enum):
    HUMAN = "human"
    AUTONOMOUS_ROBOT = "autonomous_robot"
    TELEOPERATED_ROBOT = "teleoperated_robot"
    SEMI_AUTONOMOUS = "semi_autonomous"
    HYBRID = "hybrid"


class AttestationMode(str, Enum):
    SENSOR_WITNESS = "sensor-witness"
    THIRD_PARTY_WITNESS = "third-party-witness"
    CRYPTOGRAPHIC_PRESENCE = "cryptographic-presence"
    OWNER_SIGN_OFF = "owner-sign-off"


class VerifierDecision(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    REVIEW = "review"


@dataclass
class CapabilityDescriptor:
    worker_id: str
    principal_id: str
    worker_class: WorkerClass
    current_location: dict[str, Any]
    attestation_methods_supported: list[str]
    attestation_keys: list[dict[str, str]]
    available_windows: list[dict[str, str]] = field(default_factory=list)
    certifications: list[dict[str, Any]] = field(default_factory=list)
    policy_windows: list[dict[str, str]] = field(default_factory=list)
    class_extension: dict[str, Any] = field(default_factory=dict)
    as_of: Optional[str] = None
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        as_of = self.as_of or datetime.now(timezone.utc).isoformat()
        return {
            "schema_version": self.schema_version,
            "worker_id": self.worker_id,
            "principal_id": self.principal_id,
            "class": self.worker_class.value,
            "required": {
                "current_location": self.current_location,
                "available_windows": self.available_windows,
                "attestation_methods_supported": self.attestation_methods_supported,
                "certifications": self.certifications,
                "policy_windows": self.policy_windows,
                "attestation_keys": self.attestation_keys,
                "as_of": as_of,
            },
            "class_extension": self.class_extension,
        }


@dataclass
class AttestationRequirement:
    modes: list[AttestationMode]
    threshold: str  # "any" | "all" | "M-of-N"
    M: int
    N: int
    evidence_schema: list[dict[str, Any]]
    override_allowed: bool = True
    override_authority: Optional[str] = None
    override_audit_required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "modes": [m.value for m in self.modes],
            "threshold": self.threshold,
            "M": self.M,
            "N": self.N,
            "evidence_schema": self.evidence_schema,
            "override_allowed": self.override_allowed,
            "override_authority": self.override_authority
            or "did:wcp:default-operator-ops",
            "override_audit_required": self.override_audit_required,
        }


@dataclass
class SettlementSplitEntry:
    party: str
    pct: float

    def to_dict(self) -> dict[str, Any]:
        return {"party": self.party, "pct": self.pct}


@dataclass
class Settlement:
    currency: str
    amount: str
    escrow_provider: str
    split: list[SettlementSplitEntry]
    partial_completion_schedule: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "currency": self.currency,
            "amount": self.amount,
            "escrow_provider": self.escrow_provider,
            "split": [e.to_dict() for e in self.split],
        }
        if self.partial_completion_schedule:
            out["partial_completion_schedule"] = self.partial_completion_schedule
        return out


@dataclass
class TaskDescriptor:
    task_id: str
    posted_by: str
    descriptor_type: str
    descriptor_payload: dict[str, Any]
    constraints: dict[str, Any]
    attestation_requirement: AttestationRequirement
    settlement: Settlement
    supervision: dict[str, Any] = field(default_factory=lambda: {"default": "autonomous"})
    x_subcontract_allowed: bool = False
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "task_id": self.task_id,
            "posted_by": self.posted_by,
            "descriptor_type": self.descriptor_type,
            "descriptor_payload": self.descriptor_payload,
            "constraints": self.constraints,
            "attestation_requirement": self.attestation_requirement.to_dict(),
            "settlement": self.settlement.to_dict(),
            "supervision": self.supervision,
            "x-subcontract-allowed": self.x_subcontract_allowed,
        }


@dataclass
class AttestationEvidence:
    mode: AttestationMode
    kind: str
    payload: dict[str, Any]
    payload_hash: str
    sig: str
    worker_id: str
    claim_id: str
    collected_at: str
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "mode": self.mode.value,
            "kind": self.kind,
            "payload": self.payload,
            "payload_hash": self.payload_hash,
            "sig": self.sig,
            "worker_id": self.worker_id,
            "claim_id": self.claim_id,
            "collected_at": self.collected_at,
        }
