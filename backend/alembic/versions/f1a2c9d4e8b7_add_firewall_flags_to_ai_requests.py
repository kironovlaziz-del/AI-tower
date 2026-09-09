"""add firewall_flags to ai_requests

Revision ID: f1a2c9d4e8b7
Revises: b5fd4df5a153
Create Date: 2026-09-05 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = 'f1a2c9d4e8b7'
down_revision: Union[str, None] = 'b5fd4df5a153'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('ai_requests', sa.Column('firewall_flags', JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column('ai_requests', 'firewall_flags')
