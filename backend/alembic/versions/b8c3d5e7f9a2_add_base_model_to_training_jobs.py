"""add base_model to training_jobs, make algorithm nullable

Revision ID: b8c3d5e7f9a2
Revises: a7b2c4d6e8f1
Create Date: 2026-09-06 00:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8c3d5e7f9a2'
down_revision: Union[str, None] = 'a7b2c4d6e8f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('training_jobs', sa.Column('base_model', sa.String(length=255), nullable=True))
    op.alter_column('training_jobs', 'algorithm', existing_type=sa.String(length=50), nullable=True)


def downgrade() -> None:
    op.alter_column('training_jobs', 'algorithm', existing_type=sa.String(length=50), nullable=False)
    op.drop_column('training_jobs', 'base_model')
