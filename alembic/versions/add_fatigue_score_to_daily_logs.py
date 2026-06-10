"""add fatigue_score to daily_logs

Revision ID: a1b2c3d4e5f6
Revises: <poprzednia_rewizja>
Create Date: 2026-06-11

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = None   # ← zastąp ID poprzedniej rewizji
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "daily_logs",
        sa.Column("fatigue_score", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("daily_logs", "fatigue_score")
