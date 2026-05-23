"""Add users profile image URL.

Revision ID: 0011_add_users_profile_image_url
Revises: 0010_add_auth_identities
Create Date: 2026-05-23 11:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0011_add_users_profile_image_url"
down_revision: Union[str, Sequence[str], None] = "0010_add_auth_identities"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("profile_image_url", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "profile_image_url")
