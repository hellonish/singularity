"""add_foreign_key_indexes

Revision ID: 603bac1429aa
Revises: 20260713_user_walkthroughs
Create Date: 2026-07-14 15:09:55.387876
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '603bac1429aa'
down_revision: Union[str, Sequence[str], None] = '20260713_user_walkthroughs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    existing_indexes = {
        index["name"]
        for table in (
            "chat_summaries",
            "messages",
            "report_versions",
            "usage_history",
        )
        for index in inspect(bind).get_indexes(table)
    }
    indexes = (
        ("ix_chat_summaries_through_message_id", "chat_summaries", ["through_message_id"]),
        ("ix_messages_parent_message_id", "messages", ["parent_message_id"]),
        ("ix_report_versions_parent_version_id", "report_versions", ["parent_version_id"]),
        ("ix_usage_history_chat_id", "usage_history", ["chat_id"]),
        ("ix_usage_history_report_id", "usage_history", ["report_id"]),
    )
    for name, table, columns in indexes:
        if name not in existing_indexes:
            op.create_index(name, table, columns)


def downgrade() -> None:
    """Downgrade schema."""
    for name, table in (
        ("ix_usage_history_report_id", "usage_history"),
        ("ix_usage_history_chat_id", "usage_history"),
        ("ix_report_versions_parent_version_id", "report_versions"),
        ("ix_messages_parent_message_id", "messages"),
        ("ix_chat_summaries_through_message_id", "chat_summaries"),
    ):
        op.drop_index(name, table_name=table)
