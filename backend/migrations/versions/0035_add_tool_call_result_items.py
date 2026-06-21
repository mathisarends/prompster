"""Add result_items to session tool calls.

Revision ID: 0035_add_tool_call_result_items
Revises: 0034_add_active_session_runs
Create Date: 2026-06-21

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0035_add_tool_call_result_items"
down_revision: str | Sequence[str] | None = "0034_add_active_session_runs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "session_tool_calls",
        sa.Column("result_items", postgresql.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("session_tool_calls", "result_items")
