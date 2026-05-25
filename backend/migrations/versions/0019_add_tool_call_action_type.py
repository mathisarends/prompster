"""Add tool call action type.

Revision ID: 0019_add_tool_call_action_type
Revises: 0018_add_session_user_message_attachments
Create Date: 2026-05-25 12:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0019_add_tool_call_action_type"
down_revision: Union[str, Sequence[str], None] = (
    "0018_add_session_user_message_attachments"
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "session_tool_calls",
        sa.Column("function_action_type", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("session_tool_calls", "function_action_type")
