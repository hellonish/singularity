"""Add last_four to user_llm_credentials; strength CHECK constraints; compound credential index

- user_llm_credentials.last_four VARCHAR(4): stores masked key suffix at write time
  so reads never need to decrypt the secret just for display.
- CHECK constraints on research_jobs.strength and reports.strength (1–3).
- Replace single-column index idx_user_llm_credentials_user with a compound
  (user_id, provider) index that matches the most common lookup pattern.

Revision ID: 0007
Revises: 0006
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------ last_four column
    op.add_column(
        "user_llm_credentials",
        sa.Column("last_four", sa.String(4), nullable=True),
    )

    # ------------------------------------------------------------------ strength CHECK constraints
    op.create_check_constraint(
        "ck_research_job_strength",
        "research_jobs",
        "strength BETWEEN 1 AND 3",
    )
    op.create_check_constraint(
        "ck_report_strength",
        "reports",
        "strength BETWEEN 1 AND 3",
    )

    # ------------------------------------------------------------------ credential index swap
    op.drop_index("idx_user_llm_credentials_user", table_name="user_llm_credentials")
    op.create_index(
        "idx_user_llm_credentials_user_provider",
        "user_llm_credentials",
        ["user_id", "provider"],
    )


def downgrade() -> None:
    op.drop_index("idx_user_llm_credentials_user_provider", table_name="user_llm_credentials")
    op.create_index(
        "idx_user_llm_credentials_user",
        "user_llm_credentials",
        ["user_id"],
    )
    op.drop_constraint("ck_report_strength", "reports", type_="check")
    op.drop_constraint("ck_research_job_strength", "research_jobs", type_="check")
    op.drop_column("user_llm_credentials", "last_four")
