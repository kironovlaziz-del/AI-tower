"""add error_message to ai_requests

Revision ID: d5e6f7a8b9c1
Revises: c3d5e7f9a1b4
Create Date: 2026-09-12 02:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d5e6f7a8b9c1"
down_revision: Union[str, None] = "c3d5e7f9a1b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ai_requests", sa.Column("error_message", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("ai_requests", "error_message")
