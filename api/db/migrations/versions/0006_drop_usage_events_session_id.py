"""Remove usage_events.session_id (unused after request-ID middleware removal)

Revision ID: 0006
Revises: 0005
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("usage_events", "session_id")


def downgrade() -> None:
    op.add_column(
        "usage_events",
        sa.Column("session_id", sa.String(), nullable=True),
    )
