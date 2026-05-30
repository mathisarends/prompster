"""Remove session follow-up questions.

Revision ID: 0026_remove_session_follow_up_questions
Revises: 0025_add_session_phase
Create Date: 2026-05-30 00:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0026_remove_session_follow_up_questions"
down_revision: Union[str, Sequence[str], None] = "0025_add_session_phase"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("session_follow_up_questions")
    op.drop_index(
        "ix_session_follow_up_question_groups_session_position",
        table_name="session_follow_up_question_groups",
    )
    op.drop_table("session_follow_up_question_groups")


def downgrade() -> None:
    op.create_table(
        "session_follow_up_question_groups",
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
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
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_session_follow_up_question_groups_session_position",
        "session_follow_up_question_groups",
        ["session_id", "position"],
        unique=False,
    )
    op.create_table(
        "session_follow_up_questions",
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("options", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=True),
        sa.Column("answered_option_id", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["session_follow_up_question_groups.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
