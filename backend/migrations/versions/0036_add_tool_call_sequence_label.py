"""Add label to session tool call sequences.

Revision ID: 0036_add_tool_call_sequence_label
Revises: 0035_add_tool_call_result_items
Create Date: 2026-06-21

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0036_add_tool_call_sequence_label"
down_revision: str | Sequence[str] | None = "0035_add_tool_call_result_items"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "session_tool_call_sequences",
        sa.Column("label", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("session_tool_call_sequences", "label")
