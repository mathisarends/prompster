"""Add playlist PDF export cache metadata.

Revision ID: 0037_add_playlist_pdf_export_cache
Revises: 0036_add_tool_call_sequence_label
Create Date: 2026-06-21

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0037_add_playlist_pdf_export_cache"
down_revision: str | Sequence[str] | None = "0036_add_tool_call_sequence_label"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "sessions",
        sa.Column("playlist_pdf_storage_key", sa.Text(), nullable=True),
    )
    op.add_column(
        "sessions",
        sa.Column("playlist_pdf_fingerprint", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("sessions", "playlist_pdf_fingerprint")
    op.drop_column("sessions", "playlist_pdf_storage_key")
