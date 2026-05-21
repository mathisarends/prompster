"""Add oauth connections table.

Revision ID: 0006_add_oauth_connections
Revises: 0005_add_session_starred_flag
Create Date: 2026-05-21 12:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0006_add_oauth_connections"
down_revision: Union[str, Sequence[str], None] = "0005_add_session_starred_flag"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "oauth_connections",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.text("now()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("provider_user_id", sa.String(), nullable=False),
        sa.Column("refresh_token_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column("scope", sa.String(), nullable=False),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_oauth_connections_user_provider",
        "oauth_connections",
        ["user_id", "provider"],
        unique=True,
    )
    op.create_index(
        "ix_oauth_connections_provider_user_id",
        "oauth_connections",
        ["provider_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_oauth_connections_provider_user_id", table_name="oauth_connections"
    )
    op.drop_index("ix_oauth_connections_user_provider", table_name="oauth_connections")
    op.drop_table("oauth_connections")
