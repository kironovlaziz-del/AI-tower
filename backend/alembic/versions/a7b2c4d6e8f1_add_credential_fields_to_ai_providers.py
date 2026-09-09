"""add credential fields to ai_providers

Revision ID: a7b2c4d6e8f1
Revises: f6a1b3c5d7e0
Create Date: 2026-09-06 00:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7b2c4d6e8f1'
down_revision: Union[str, None] = 'f6a1b3c5d7e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('ai_providers', sa.Column('base_url', sa.String(length=500), nullable=True))
    op.add_column('ai_providers', sa.Column('default_model', sa.String(length=255), nullable=True))
    op.add_column('ai_providers', sa.Column('api_key_encrypted', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('ai_providers', 'api_key_encrypted')
    op.drop_column('ai_providers', 'default_model')
    op.drop_column('ai_providers', 'base_url')
