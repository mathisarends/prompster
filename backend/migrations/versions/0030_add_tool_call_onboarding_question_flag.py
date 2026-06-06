"""Add tool call onboarding-question flag.

Revision ID: 0030_add_tool_call_onboarding_question_flag
Revises: 0029_add_onboarding_multi_select
Create Date: 2026-06-06

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0030_add_tool_call_onboarding_question_flag"
down_revision: str | Sequence[str] | None = "0029_add_onboarding_multi_select"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "session_tool_calls",
        sa.Column(
            "function_is_onboarding_question",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )
    op.alter_column(
        "session_tool_calls",
        "function_is_onboarding_question",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column("session_tool_calls", "function_is_onboarding_question")
