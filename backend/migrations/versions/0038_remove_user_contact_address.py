"""Remove the obsolete contact address from user records.

Revision ID: 0038_remove_user_contact_address
Revises: 0037_add_playlist_pdf_export_cache
Create Date: 2026-09-10 00:00:00
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0038_remove_user_contact_address"
down_revision: Union[str, Sequence[str], None] = "0037_add_playlist_pdf_export_cache"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_users_email")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS email")


def downgrade() -> None:
    raise RuntimeError("Restoring removed contact addresses is not supported")
