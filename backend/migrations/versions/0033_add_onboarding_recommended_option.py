"""Add onboarding question recommended option.

Revision ID: 0033_add_onboarding_recommended_option
Revises: 0032_add_session_user_message_image_attachments
Create Date: 2026-06-19

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0033_add_onboarding_recommended_option"
down_revision: str | Sequence[str] | None = (
    "0032_add_session_user_message_image_attachments"
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "session_onboarding_questions",
        sa.Column("recommended_option", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("session_onboarding_questions", "recommended_option")
