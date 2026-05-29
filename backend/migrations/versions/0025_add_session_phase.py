"""Add persistent session phase.

Revision ID: 0025_add_session_phase
Revises: 0024_add_session_references
Create Date: 2026-05-29 00:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0025_add_session_phase"
down_revision: Union[str, Sequence[str], None] = "0024_add_session_references"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "sessions",
        sa.Column(
            "phase",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'build'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("sessions", "phase")
