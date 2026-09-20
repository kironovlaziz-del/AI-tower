"""add signed_payload to delegation_hops

Revision ID: d5e7f9a1b3c5
Revises: c4d6e8f0a2b4
Create Date: 2026-09-20 01:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d5e7f9a1b3c5"
down_revision: Union[str, None] = "c4d6e8f0a2b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "delegation_hops",
        sa.Column("signed_payload", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("delegation_hops", "signed_payload")
