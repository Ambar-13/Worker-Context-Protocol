"""initial wcp tables

Revision ID: 0001_initial_wcp_tables
Revises:
Create Date: 2026-05-23

Creates the 7 WCP coordinator tables and 4 enum types. Designed to merge into
the existing Rentably alembic chain via `down_revision = <last-rentably-rev>`.
INTEGRATION-GAP: set down_revision to the principal's current head before
running alembic upgrade.
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial_wcp_tables"
down_revision = None  # INTEGRATION-GAP: set to existing head
branch_labels = None
depends_on = None


def upgrade() -> None:
    from wcp_coordinator.models import Base
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    from wcp_coordinator.models import Base
    Base.metadata.drop_all(bind=op.get_bind())
