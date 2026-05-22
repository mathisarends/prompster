"""Rename tool call groups to sequences.

Revision ID: 0007_rename_tool_call_groups_to_sequences
Revises: 0006_add_oauth_connections
Create Date: 2026-05-21 15:30:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0007_rename_tool_call_groups_to_sequences"
down_revision: Union[str, Sequence[str], None] = "0006_add_oauth_connections"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "session_tool_calls_group_id_fkey",
        "session_tool_calls",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_session_tool_call_groups_session_position",
        table_name="session_tool_call_groups",
    )
    op.rename_table("session_tool_call_groups", "session_tool_call_sequences")
    op.create_index(
        "ix_session_tool_call_sequences_session_position",
        "session_tool_call_sequences",
        ["session_id", "position"],
        unique=False,
    )
    op.alter_column(
        "session_tool_calls",
        "group_id",
        new_column_name="sequence_id",
        existing_type=postgresql.UUID(as_uuid=True),
        existing_nullable=False,
    )
    op.create_foreign_key(
        "fk_session_tool_calls_sequence_id_session_tool_call_sequences",
        "session_tool_calls",
        "session_tool_call_sequences",
        ["sequence_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_session_tool_calls_sequence_id_session_tool_call_sequences",
        "session_tool_calls",
        type_="foreignkey",
    )
    op.alter_column(
        "session_tool_calls",
        "sequence_id",
        new_column_name="group_id",
        existing_type=postgresql.UUID(as_uuid=True),
        existing_nullable=False,
    )
    op.drop_index(
        "ix_session_tool_call_sequences_session_position",
        table_name="session_tool_call_sequences",
    )
    op.rename_table("session_tool_call_sequences", "session_tool_call_groups")
    op.create_index(
        "ix_session_tool_call_groups_session_position",
        "session_tool_call_groups",
        ["session_id", "position"],
        unique=False,
    )
    op.create_foreign_key(
        "session_tool_calls_group_id_fkey",
        "session_tool_calls",
        "session_tool_call_groups",
        ["group_id"],
        ["id"],
        ondelete="CASCADE",
    )
