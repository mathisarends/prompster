"""Add tool call status label.

Revision ID: 0008_add_tool_call_status_label
Revises: 0007_rename_tool_call_groups_to_sequences
Create Date: 2026-05-22 06:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0008_add_tool_call_status_label"
down_revision: Union[str, Sequence[str], None] = (
    "0007_rename_tool_call_groups_to_sequences"
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "session_tool_calls",
        sa.Column("function_status_label", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("session_tool_calls", "function_status_label")
