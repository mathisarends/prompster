"""Cascade session onboarding question deletes.

Revision ID: 0028_cascade_onboarding_deletes
Revises: 0027_add_onboarding_questions_table
Create Date: 2026-05-30 00:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "0028_cascade_onboarding_deletes"
down_revision: Union[str, Sequence[str], None] = "0027_add_onboarding_questions_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "session_onboarding_questions_session_id_fkey",
        "session_onboarding_questions",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "session_onboarding_questions_session_id_fkey",
        "session_onboarding_questions",
        "sessions",
        ["session_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        "session_onboarding_questions_session_id_fkey",
        "session_onboarding_questions",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "session_onboarding_questions_session_id_fkey",
        "session_onboarding_questions",
        "sessions",
        ["session_id"],
        ["id"],
    )
