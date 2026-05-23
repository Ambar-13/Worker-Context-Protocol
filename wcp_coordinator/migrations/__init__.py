"""
Alembic-style migration entry points for the wcp_coordinator tables.

For v0.1, callers may bootstrap directly via `Base.metadata.create_all(engine)`.
Production deployments wire this into the existing Rentably Alembic chain via
the function `register_with_alembic` below. INTEGRATION-GAP: the principal
will provide the existing alembic env.py and we register our metadata into
the same target.
"""
from __future__ import annotations

from sqlalchemy import Engine

from ..models import Base


def create_all(engine: Engine) -> None:
    """Bootstrap: create all WCP tables. v0.1 simple path; not for production."""
    Base.metadata.create_all(engine)


def drop_all(engine: Engine) -> None:
    Base.metadata.drop_all(engine)
