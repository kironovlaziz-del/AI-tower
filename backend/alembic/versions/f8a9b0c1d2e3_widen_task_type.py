"""widen training_jobs.task_type from 30 to 50 chars

Revision ID: f8a9b0c1d2e3
Revises: e6f7a8b9c0d1
Create Date: 2026-09-12 04:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f8a9b0c1d2e3"
down_revision: Union[str, None] = "e6f7a8b9c0d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # "transformer_text_classification" is 33 chars and does not fit in the
    # original VARCHAR(30). Widen the column so transformer-track jobs can
    # be created.
    op.alter_column(
        "training_jobs",
        "task_type",
        existing_type=sa.String(length=30),
        type_=sa.String(length=50),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "training_jobs",
        "task_type",
        existing_type=sa.String(length=50),
        type_=sa.String(length=30),
        existing_nullable=False,
    )
