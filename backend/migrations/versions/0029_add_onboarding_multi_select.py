"""Add onboarding multi-select metadata.

Revision ID: 0029_add_onboarding_multi_select
Revises: 0028_cascade_onboarding_deletes
Create Date: 2026-06-05

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0029_add_onboarding_multi_select"
down_revision: str | Sequence[str] | None = "0028_cascade_onboarding_deletes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "session_onboarding_questions",
        sa.Column(
            "selection_mode",
            sa.String(length=32),
            server_default=sa.text("'single_select'"),
            nullable=False,
        ),
    )
    op.add_column(
        "session_onboarding_questions",
        sa.Column(
            "answers",
            sa.JSON(),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
    )
    op.execute(
        """
        UPDATE session_onboarding_questions
        SET answers = json_build_array(answer)
        WHERE answer IS NOT NULL AND answer <> ''
        """
    )
    op.alter_column("session_onboarding_questions", "answers", server_default=None)


def downgrade() -> None:
    op.drop_column("session_onboarding_questions", "answers")
    op.drop_column("session_onboarding_questions", "selection_mode")
