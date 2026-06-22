"""add discord reminder fields to users

Revision ID: 72efb594294f
Revises: c8b1f3d9a77d
Create Date: 2026-06-22 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "72efb594294f"
down_revision: Union[str, Sequence[str], None] = "c8b1f3d9a77d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("discord_user_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("discord_connect_code", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("discord_connect_code_expires_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("reminder_time", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("reminder_enabled", sa.Boolean(), nullable=False, server_default=sa.text("0")))
        batch_op.add_column(sa.Column("last_reminder_sent_date", sa.Date(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("last_reminder_sent_date")
        batch_op.drop_column("reminder_enabled")
        batch_op.drop_column("reminder_time")
        batch_op.drop_column("discord_connect_code_expires_at")
        batch_op.drop_column("discord_connect_code")
        batch_op.drop_column("discord_user_id")
