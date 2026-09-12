"""Add progress tracking columns to training_jobs

Revision ID: a2c4e6f8b0d2
Revises: f7a3b9c1d2e4
Create Date: 2026-09-12 00:30:00.000000

Long-running fine-tunes previously had no visible progress — the UI just
showed a spinner for hours. These columns are updated by a transformers
TrainerCallback (see training_tasks.py) on each logging step so the
frontend can render a progress bar.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a2c4e6f8b0d2"
down_revision: Union[str, None] = "f7a3b9c1d2e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "training_jobs",
        sa.Column("progress_pct", sa.Float(), nullable=True),
    )
    op.add_column(
        "training_jobs",
        sa.Column("progress_stage", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("training_jobs", "progress_stage")
    op.drop_column("training_jobs", "progress_pct")
