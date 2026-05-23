"""SQLAlchemy ORM models."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Coordinator(Base):
    """A registered coordinator descriptor.

    The full signed descriptor is preserved verbatim in `descriptor_json`
    so that a verifier can re-check the signature against the bytes the
    coordinator originally posted (no re-serialisation drift).
    """

    __tablename__ = "coordinators"

    did: Mapped[str] = mapped_column(String(256), primary_key=True)
    endpoint: Mapped[str] = mapped_column(String(2048))
    operator: Mapped[str] = mapped_column(String(512))
    operator_country: Mapped[str] = mapped_column(String(8))
    conformance_level: Mapped[int] = mapped_column(Integer)
    descriptor_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    public_key_multibase: Mapped[str] = mapped_column(String(256))
    signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_alive_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
