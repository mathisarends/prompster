"""Add agent checkpoints.

Revision ID: 0040_add_session_agent_checkpoints
Revises: 0039_remove_user_message_quotas
Create Date: 2026-11-24 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0040_add_session_agent_checkpoints"
down_revision: Union[str, Sequence[str], None] = "0039_remove_user_message_quotas"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "session_agent_checkpoints",
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("state", postgresql.JSONB(), nullable=False),
        sa.Column("execution", postgresql.JSONB(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_table("session_agent_checkpoints")
