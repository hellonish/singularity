"""Create the initial durable application schema.

Revision ID: 20260712_research_run_events
Revises:
Create Date: 2026-07-12
"""
from alembic import op

from api.models import Base


revision = "20260712_research_run_events"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # This project previously bootstrapped tables at API startup.  Use one
    # baseline revision to migrate a fresh deployment before the API/worker
    # starts; later schema changes must be explicit Alembic revisions.
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
