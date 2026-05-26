"""Add daily check-in fields

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
        batch_op.add_column(sa.Column("sleep_quality", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("energy_level", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("stress_level", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("sleep_start", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("sleep_end", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("sleep_duration_minutes", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("mood_score", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("training_rpe", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("waist_cm", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("chest_cm", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("photo_path", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("eaten_meals_json", sa.String(), nullable=False, server_default="[]"))


def downgrade() -> None:
    with op.batch_alter_table("daily_logs") as batch_op:
        batch_op.drop_column("eaten_meals_json")
        batch_op.drop_column("photo_path")
        batch_op.drop_column("chest_cm")
        batch_op.drop_column("waist_cm")
        batch_op.drop_column("training_rpe")
        batch_op.drop_column("mood_score")
        batch_op.drop_column("sleep_duration_minutes")
        batch_op.drop_column("sleep_end")
        batch_op.drop_column("sleep_start")
        batch_op.drop_column("stress_level")
        batch_op.drop_column("energy_level")
        batch_op.drop_column("sleep_quality")
