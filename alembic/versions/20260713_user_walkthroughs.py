"""Add user_walkthroughs for at-most-once walkthrough claims.

Revision ID: 20260713_user_walkthroughs
Revises: 20260712_add_openrouter_provider
Create Date: 2026-07-13
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "20260713_user_walkthroughs"
down_revision = "20260712_add_openrouter_provider"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The baseline revision bootstraps a fresh database with ``create_all`` of
    # the current models, so a brand-new deploy already has this table. Only
    # databases stamped before this revision need it created; guard so both
    # paths converge on the same schema.
    if "user_walkthroughs" in inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "user_walkthroughs",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("walkthrough_key", sa.String(length=100), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="claimed"),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_user_walkthroughs_user_id_users", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint(
            "user_id", "walkthrough_key", "version", name="pk_user_walkthroughs"
        ),
        sa.CheckConstraint(
            "status IN ('claimed', 'completed', 'dismissed')",
            name="ck_user_walkthroughs_user_walkthrough_status",
        ),
    )
    op.create_index(
        "ix_user_walkthroughs_user_status", "user_walkthroughs", ["user_id", "status"]
    )


def downgrade() -> None:
    if "user_walkthroughs" not in inspect(op.get_bind()).get_table_names():
        return
    op.drop_index("ix_user_walkthroughs_user_status", table_name="user_walkthroughs")
    op.drop_table("user_walkthroughs")
