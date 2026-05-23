"""
SQLAlchemy 2.0 ORM models for the WCP coordinator.

Tables: WcpWorker, WcpTask, WcpClaim, WcpSession, WcpAttestation, WcpAudit,
WcpSubscription. Enum types for class, state, attestation mode, verifier decision.

Reuses the existing Rentably Postgres instance when merged into the Rentably stack.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base for all WCP coordinator models."""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid_str() -> str:
    return str(uuid.uuid4())


class WorkerClass(str, enum.Enum):
    HUMAN = "human"
    AUTONOMOUS_ROBOT = "autonomous_robot"
    TELEOPERATED_ROBOT = "teleoperated_robot"
    SEMI_AUTONOMOUS = "semi_autonomous"
    HYBRID = "hybrid"


class TaskState(str, enum.Enum):
    POSTED = "posted"
    CLAIMED = "claimed"
    EXECUTING = "executing"
    SUPERVISING = "supervising"
    ATTESTING = "attesting"
    SETTLED = "settled"
    DISPUTED = "disputed"
    REFUNDED = "refunded"
    ABORTED = "aborted"


class AttestationMode(str, enum.Enum):
    SENSOR_WITNESS = "sensor-witness"
    THIRD_PARTY_WITNESS = "third-party-witness"
    CRYPTOGRAPHIC_PRESENCE = "cryptographic-presence"
    OWNER_SIGN_OFF = "owner-sign-off"


class VerifierDecision(str, enum.Enum):
    PASS = "pass"
    FAIL = "fail"
    REVIEW = "review"


class WcpWorker(Base):
    __tablename__ = "wcp_workers"

    worker_id: Mapped[str] = mapped_column(String, primary_key=True)
    principal_id: Mapped[str] = mapped_column(String, nullable=False)
    worker_class: Mapped[WorkerClass] = mapped_column(
        Enum(WorkerClass, name="wcp_worker_class"), nullable=False
    )
    capabilities_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ttl_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=3600)
    as_of: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    claims: Mapped[list["WcpClaim"]] = relationship(back_populates="worker")

    __table_args__ = (Index("ix_wcp_workers_principal", "principal_id"),)


class WcpTask(Base):
    __tablename__ = "wcp_tasks"

    task_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid_str)
    posted_by: Mapped[str] = mapped_column(String, nullable=False)
    descriptor_type: Mapped[str] = mapped_column(String, nullable=False)
    task_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    bond_ref: Mapped[str] = mapped_column(String, nullable=False)
    expiry: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    state: Mapped[TaskState] = mapped_column(
        Enum(TaskState, name="wcp_task_state"),
        nullable=False,
        default=TaskState.POSTED,
    )
    posted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    claims: Mapped[list["WcpClaim"]] = relationship(back_populates="task")

    __table_args__ = (
        Index("ix_wcp_tasks_state", "state"),
        Index("ix_wcp_tasks_descriptor_type", "descriptor_type"),
    )


class WcpClaim(Base):
    __tablename__ = "wcp_claims"

    claim_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid_str)
    task_id: Mapped[str] = mapped_column(
        String, ForeignKey("wcp_tasks.task_id"), nullable=False
    )
    worker_id: Mapped[str] = mapped_column(
        String, ForeignKey("wcp_workers.worker_id"), nullable=False
    )
    bid_amount: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    eta: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    acceptance_attestation_json: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False
    )
    accepted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    claimed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    last_heartbeat_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    task: Mapped[WcpTask] = relationship(back_populates="claims")
    worker: Mapped[WcpWorker] = relationship(back_populates="claims")

    __table_args__ = (
        Index("ix_wcp_claims_task_state", "task_id", "accepted"),
        Index("ix_wcp_claims_heartbeat", "last_heartbeat_at"),
    )


class WcpSession(Base):
    """An execute session bound to a claim."""

    __tablename__ = "wcp_sessions"

    session_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid_str)
    claim_id: Mapped[str] = mapped_column(
        String, ForeignKey("wcp_claims.claim_id"), nullable=False
    )
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    events_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class WcpAttestation(Base):
    __tablename__ = "wcp_attestations"

    attestation_id: Mapped[str] = mapped_column(
        String, primary_key=True, default=_uuid_str
    )
    claim_id: Mapped[str] = mapped_column(
        String, ForeignKey("wcp_claims.claim_id"), nullable=False
    )
    mode: Mapped[AttestationMode] = mapped_column(
        Enum(AttestationMode, name="wcp_attestation_mode"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String, nullable=False)
    payload_hash: Mapped[str] = mapped_column(String, nullable=False)
    sig: Mapped[str] = mapped_column(Text, nullable=False)
    worker_id: Mapped[str] = mapped_column(String, nullable=False)
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    verifier_decision: Mapped[Optional[VerifierDecision]] = mapped_column(
        Enum(VerifierDecision, name="wcp_verifier_decision"), nullable=True
    )
    verifier_reasons: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class WcpAudit(Base):
    """Hash-linked audit chain entry. One per state transition."""

    __tablename__ = "wcp_audit"

    entry_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid_str)
    claim_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    task_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    actor_did: Mapped[str] = mapped_column(String, nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    payload_hash: Mapped[str] = mapped_column(String, nullable=False)
    prev_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    this_hash: Mapped[str] = mapped_column(String, nullable=False)
    sig: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        Index("ix_wcp_audit_claim", "claim_id"),
        Index("ix_wcp_audit_task", "task_id"),
        Index("ix_wcp_audit_timestamp", "timestamp"),
    )


class WcpSubscription(Base):
    __tablename__ = "wcp_subscriptions"

    subscription_id: Mapped[str] = mapped_column(
        String, primary_key=True, default=_uuid_str
    )
    agent_did: Mapped[str] = mapped_column(String, nullable=False)
    filter_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    since_revision: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    stream_endpoint: Mapped[str] = mapped_column(String, nullable=False)
    ttl_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=3600)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
