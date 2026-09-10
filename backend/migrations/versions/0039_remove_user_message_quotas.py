"""Remove user message quotas.

Revision ID: 0039_remove_user_message_quotas
Revises: 0038_remove_user_contact_address
Create Date: 2026-09-10 00:00:00
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0039_remove_user_message_quotas"
down_revision: Union[str, Sequence[str], None] = "0038_remove_user_contact_address"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("user_message_quotas")


def downgrade() -> None:
    raise RuntimeError("Restoring removed user message quotas is not supported")
