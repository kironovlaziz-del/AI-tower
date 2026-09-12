"""make target_column nullable on training_jobs

Revision ID: d0e5f7a9b1c4
Revises: c9d4e6f8a0b3
Create Date: 2026-09-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd0e5f7a9b1c4'
down_revision: Union[str, None] = 'c9d4e6f8a0b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'training_jobs', 'target_column',
        existing_type=sa.String(length=255), nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        'training_jobs', 'target_column',
        existing_type=sa.String(length=255), nullable=False,
    )
