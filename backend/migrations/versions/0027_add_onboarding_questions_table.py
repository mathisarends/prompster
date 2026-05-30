"""Add session onboarding questions table.

Revision ID: 0027_add_onboarding_questions_table
Revises: 0026_remove_session_follow_up_questions
Create Date: 2026-05-30 00:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0027_add_onboarding_questions_table"
down_revision: Union[str, Sequence[str], None] = (
    "0026_remove_session_follow_up_questions"
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "sessions",
        "phase",
        existing_type=sa.String(length=32),
        server_default=sa.text("'onboarding'"),
        existing_nullable=False,
    )

    op.create_table(
        "session_onboarding_questions",
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("question_text", sa.String(), nullable=False),
        sa.Column(
            "options",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
        sa.Column(
            "is_last_question",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("answer", sa.String(), nullable=True),
        sa.Column(
            "is_answered",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_session_onboarding_questions_session_sequence",
        "session_onboarding_questions",
        ["session_id", "sequence_number"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_session_onboarding_questions_session_sequence",
        table_name="session_onboarding_questions",
    )
    op.drop_table("session_onboarding_questions")

    op.alter_column(
        "sessions",
        "phase",
        existing_type=sa.String(length=32),
        server_default=sa.text("'build'"),
        existing_nullable=False,
    )
