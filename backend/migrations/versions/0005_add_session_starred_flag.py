"""Add session is_starred flag.

Revision ID: 0005_add_session_starred_flag
Revises: 0004_split_session_entries
Create Date: 2026-05-19 13:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0005_add_session_starred_flag"
down_revision: Union[str, Sequence[str], None] = "0004_split_session_entries"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "sessions",
        sa.Column(
            "is_starred",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("sessions", "is_starred")
