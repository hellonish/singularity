"""Allow OpenRouter credentials alongside Groq and DeepSeek.

Revision ID: 20260712_add_openrouter_provider
Revises: 20260712_research_run_events
Create Date: 2026-07-12
"""
from alembic import op


revision = "20260712_add_openrouter_provider"
down_revision = "20260712_research_run_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("llm_provider_credentials") as batch:
        batch.drop_constraint("llm_credential_provider", type_="check")
        batch.create_check_constraint(
            "llm_credential_provider",
            "provider IN ('groq', 'deepseek', 'openrouter')",
        )


def downgrade() -> None:
    with op.batch_alter_table("llm_provider_credentials") as batch:
        batch.drop_constraint("llm_credential_provider", type_="check")
        batch.create_check_constraint("llm_credential_provider", "provider IN ('groq', 'deepseek')")
