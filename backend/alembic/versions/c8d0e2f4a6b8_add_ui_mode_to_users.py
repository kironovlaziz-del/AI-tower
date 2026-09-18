"""add ui_mode preference to users

Revision ID: c8d0e2f4a6b8
Revises: b7c9d1e3f5a7
Create Date: 2026-09-17 08:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c8d0e2f4a6b8"
down_revision: Union[str, None] = "b7c9d1e3f5a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("ui_mode", sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "ui_mode")
