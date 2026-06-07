"""add_drill_metadata

Revision ID: 9d8e7f6a5b43
Revises: 7a6d4c3e9b12
Create Date: 2026-06-04 10:20:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9d8e7f6a5b43"
down_revision: Union[str, Sequence[str], None] = "7a6d4c3e9b12"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("drill_results") as batch_op:
        batch_op.add_column(sa.Column("drill_category", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("drill_sport", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("target_pct", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("drill_results") as batch_op:
        batch_op.drop_column("target_pct")
        batch_op.drop_column("drill_sport")
        batch_op.drop_column("drill_category")
