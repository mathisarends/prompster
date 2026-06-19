"""Add active session runs.

Revision ID: 0034_add_active_session_runs
Revises: 0033_add_onboarding_recommended_option
Create Date: 2026-06-19

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0034_add_active_session_runs"
down_revision: str | Sequence[str] | None = "0033_add_onboarding_recommended_option"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "active_session_runs",
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "stop_requested",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("stop_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("session_id"),
    )
    op.create_index(
        "ix_active_session_runs_run_id",
        "active_session_runs",
        ["run_id"],
        unique=False,
    )
    op.create_index(
        "ix_active_session_runs_stop_requested",
        "active_session_runs",
        ["stop_requested"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_active_session_runs_stop_requested",
        table_name="active_session_runs",
    )
    op.drop_index("ix_active_session_runs_run_id", table_name="active_session_runs")
    op.drop_table("active_session_runs")
