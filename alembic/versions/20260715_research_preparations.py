"""Add durable research preparation state.

Revision ID: 20260715_research_preparations
Revises: 603bac1429aa
"""
from alembic import op
import sqlalchemy as sa


revision = "20260715_research_preparations"
down_revision = "603bac1429aa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The legacy baseline migration calls Base.metadata.create_all(), which can
    # create current-model tables during a brand-new install. Keep this delta
    # idempotent for that path while still applying normally to deployed DBs.
    inspector = sa.inspect(op.get_bind())
    if "research_preparations" not in inspector.get_table_names():
        op.create_table(
            "research_preparations",
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("provider_credential_id", sa.String(length=36), nullable=False),
            sa.Column("query", sa.Text(), nullable=False),
            sa.Column("approval_mode", sa.String(length=12), nullable=False),
            sa.Column("status", sa.String(length=24), nullable=False),
            sa.Column("model_id", sa.String(length=255), nullable=True),
            sa.Column("strength", sa.Integer(), nullable=False),
            sa.Column("current_question_index", sa.Integer(), nullable=False),
            sa.Column("plan_data", sa.JSON(), nullable=False),
            sa.Column("answers", sa.JSON(), nullable=False),
            sa.Column("final_brief", sa.JSON(), nullable=False),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.CheckConstraint("approval_mode IN ('ask', 'auto')", name=op.f("ck_research_preparations_research_preparation_mode")),
            sa.CheckConstraint("status IN ('draft', 'awaiting_input', 'ready', 'started', 'cancelled', 'failed')", name=op.f("ck_research_preparations_research_preparation_status")),
            sa.CheckConstraint("strength >= 1 AND strength <= 3", name=op.f("ck_research_preparations_research_preparation_strength")),
            sa.ForeignKeyConstraint(["provider_credential_id"], ["llm_provider_credentials.id"], name=op.f("fk_research_preparations_provider_credential_id_llm_provider_credentials"), ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_research_preparations_user_id_users"), ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_research_preparations")),
        )
        op.create_index(op.f("ix_research_preparations_provider_credential_id"), "research_preparations", ["provider_credential_id"])
        op.create_index(op.f("ix_research_preparations_user_id"), "research_preparations", ["user_id"])
        op.create_index("ix_research_preparations_user_created", "research_preparations", ["user_id", "created_at"])
    run_columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("research_runs")}
    if "preparation_id" not in run_columns:
        with op.batch_alter_table("research_runs") as batch_op:
            batch_op.add_column(sa.Column("preparation_id", sa.String(length=36), nullable=True))
            batch_op.create_index(op.f("ix_research_runs_preparation_id"), ["preparation_id"], unique=True)
            batch_op.create_foreign_key(
                op.f("fk_research_runs_preparation_id_research_preparations"),
                "research_preparations",
                ["preparation_id"],
                ["id"],
                ondelete="SET NULL",
            )


def downgrade() -> None:
    with op.batch_alter_table("research_runs") as batch_op:
        batch_op.drop_constraint(op.f("fk_research_runs_preparation_id_research_preparations"), type_="foreignkey")
        batch_op.drop_index(op.f("ix_research_runs_preparation_id"))
        batch_op.drop_column("preparation_id")
    op.drop_index("ix_research_preparations_user_created", table_name="research_preparations")
    op.drop_index(op.f("ix_research_preparations_user_id"), table_name="research_preparations")
    op.drop_index(op.f("ix_research_preparations_provider_credential_id"), table_name="research_preparations")
    op.drop_table("research_preparations")
