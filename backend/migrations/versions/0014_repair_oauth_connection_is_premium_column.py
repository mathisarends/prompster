"""Repair oauth_connections.is_premium column.

Revision ID: 0014_repair_oauth_connection_is_premium_column
Revises: 0013_add_oauth_connection_is_premium
Create Date: 2026-05-23 13:30:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0014_repair_oauth_connection_is_premium_column"
down_revision: Union[str, Sequence[str], None] = "0013_add_oauth_connection_is_premium"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(*, table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def upgrade() -> None:
    if not _has_column(table_name="oauth_connections", column_name="is_premium"):
        op.add_column(
            "oauth_connections",
            sa.Column(
                "is_premium",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )

    op.execute(
        sa.text(
            "UPDATE oauth_connections SET is_premium = false WHERE is_premium IS NULL"
        )
    )

    op.alter_column(
        "oauth_connections",
        "is_premium",
        existing_type=sa.Boolean(),
        nullable=False,
        server_default=sa.text("false"),
    )


def downgrade() -> None:
    if _has_column(table_name="oauth_connections", column_name="is_premium"):
        op.drop_column("oauth_connections", "is_premium")
