"""Map report/job strength to 3 tiers (1=low, 2=med, 3=high)

Revision ID: 0005
Revises: 0004
"""
from __future__ import annotations

from alembic import op


revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE reports SET strength = CASE
            WHEN strength <= 3 THEN 1
            WHEN strength <= 7 THEN 2
            ELSE 3
        END
        """
    )
    op.execute(
        """
        UPDATE research_jobs SET strength = CASE
            WHEN strength <= 3 THEN 1
            WHEN strength <= 7 THEN 2
            ELSE 3
        END
        """
    )
    op.alter_column("reports", "strength", server_default="2")
    op.alter_column("research_jobs", "strength", server_default="2")


def downgrade() -> None:
    op.alter_column("reports", "strength", server_default="5")
    op.alter_column("research_jobs", "strength", server_default="5")
