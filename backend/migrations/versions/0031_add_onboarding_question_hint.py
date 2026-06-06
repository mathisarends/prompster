"""Add onboarding question hint.

Revision ID: 0031_add_onboarding_question_hint
Revises: 0030_add_tool_call_onboarding_question_flag
Create Date: 2026-06-06

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0031_add_onboarding_question_hint"
down_revision: str | Sequence[str] | None = (
    "0030_add_tool_call_onboarding_question_flag"
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "session_onboarding_questions",
        sa.Column("hint", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("session_onboarding_questions", "hint")
