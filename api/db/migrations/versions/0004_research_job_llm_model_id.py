"""research_jobs: store BYOK model_id for pipeline

Revision ID: 0004
Revises: 0003
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0004"
down_revision = "0003_user_llm"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "research_jobs",
        sa.Column(
            "llm_model_id",
            sa.String(length=128),
            nullable=False,
            server_default="grok-3-mini",
        ),
    )
    op.alter_column("research_jobs", "llm_model_id", server_default=None)


def downgrade() -> None:
    op.drop_column("research_jobs", "llm_model_id")
