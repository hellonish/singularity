"""thread canonical_report_qa for default report Q&A thread

Revision ID: 0002_thread_canonical
Revises: 0001_initial
Create Date: 2026-04-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_thread_canonical"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "threads",
        sa.Column(
            "canonical_report_qa",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.create_index(
        "uq_threads_user_report_canonical",
        "threads",
        ["user_id", "report_id"],
        unique=True,
        postgresql_where=sa.text("report_id IS NOT NULL AND canonical_report_qa IS TRUE"),
    )


def downgrade() -> None:
    op.drop_index("uq_threads_user_report_canonical", table_name="threads")
    op.drop_column("threads", "canonical_report_qa")
