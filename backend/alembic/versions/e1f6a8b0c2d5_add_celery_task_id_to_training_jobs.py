"""add celery_task_id to training_jobs

Revision ID: e1f6a8b0c2d5
Revises: d0e5f7a9b1c4
Create Date: 2026-09-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1f6a8b0c2d5'
down_revision: Union[str, None] = 'd0e5f7a9b1c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('training_jobs', sa.Column('celery_task_id', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('training_jobs', 'celery_task_id')
