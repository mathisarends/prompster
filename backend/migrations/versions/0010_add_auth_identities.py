"""Add auth identities.

Revision ID: 0010_add_auth_identities
Revises: 0009_add_playlist_track_spotify_uri
Create Date: 2026-05-23 09:10:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0010_add_auth_identities"
down_revision: Union[str, Sequence[str], None] = "0009_add_playlist_track_spotify_uri"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "auth_identities",
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
        sa.Column("subject", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.execute(
        """
        INSERT INTO auth_identities (user_id, provider, subject)
        SELECT id, 'google', google_subject
        FROM users
        """
    )
    op.create_index(
        "ix_auth_identities_provider_subject",
        "auth_identities",
        ["provider", "subject"],
        unique=True,
    )
    op.create_index(
        "ix_auth_identities_user_id",
        "auth_identities",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_auth_identities_user_provider",
        "auth_identities",
        ["user_id", "provider"],
        unique=True,
    )
    op.drop_index(op.f("ix_users_google_subject"), table_name="users")
    op.drop_column("users", "google_subject")


def downgrade() -> None:
    op.add_column("users", sa.Column("google_subject", sa.String(), nullable=True))
    op.execute(
        """
        UPDATE users
        SET google_subject = auth_identities.subject
        FROM auth_identities
        WHERE auth_identities.user_id = users.id
        AND auth_identities.provider = 'google'
        """
    )
    op.execute(
        """
        UPDATE users
        SET google_subject = 'downgraded-' || id::text
        WHERE google_subject IS NULL
        """
    )
    op.alter_column("users", "google_subject", nullable=False)
    op.create_index(
        op.f("ix_users_google_subject"),
        "users",
        ["google_subject"],
        unique=True,
    )
    op.drop_index("ix_auth_identities_user_provider", table_name="auth_identities")
    op.drop_index("ix_auth_identities_user_id", table_name="auth_identities")
    op.drop_index(
        "ix_auth_identities_provider_subject",
        table_name="auth_identities",
    )
    op.drop_table("auth_identities")
