"""add day item columns to daily_logs

Revision ID: c8b1f3d9a77d
Revises: 2c4f7b8d9a10
Create Date: 2026-05-30 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c8b1f3d9a77d"
down_revision: Union[str, Sequence[str], None] = "2c4f7b8d9a10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("daily_logs") as batch_op:
        batch_op.add_column(sa.Column("meals_json", sa.Text(), nullable=False, server_default=sa.text("'[]'")))
        batch_op.add_column(sa.Column("workouts_json", sa.Text(), nullable=False, server_default=sa.text("'[]'")))
        batch_op.add_column(sa.Column("custom_meals_json", sa.Text(), nullable=False, server_default=sa.text("'[]'")))


def downgrade() -> None:
    with op.batch_alter_table("daily_logs") as batch_op:
        batch_op.drop_column("custom_meals_json")
        batch_op.drop_column("workouts_json")
        batch_op.drop_column("meals_json")
