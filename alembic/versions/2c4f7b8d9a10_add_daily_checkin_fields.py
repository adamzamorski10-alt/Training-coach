"""add_extended_checkin_fields_to_daily_logs

Revision ID: 2c4f7b8d9a10
Revises: 83a922b108b6
Create Date: 2026-05-26 21:10:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2c4f7b8d9a10"
down_revision: Union[str, Sequence[str], None] = "83a922b108b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("daily_logs") as batch_op:
        batch_op.add_column(sa.Column("sleep_hours", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("sleep_quality", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("sleep_start", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("sleep_end", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("energy_level", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("stress_level", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("mood_score", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("rpe", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("meals_eaten", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("workouts_done", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("notes", sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("daily_logs") as batch_op:
        batch_op.drop_column("notes")
        batch_op.drop_column("workouts_done")
        batch_op.drop_column("meals_eaten")
        batch_op.drop_column("rpe")
        batch_op.drop_column("mood_score")
        batch_op.drop_column("stress_level")
        batch_op.drop_column("energy_level")
        batch_op.drop_column("sleep_end")
        batch_op.drop_column("sleep_start")
        batch_op.drop_column("sleep_quality")
        batch_op.drop_column("sleep_hours")
