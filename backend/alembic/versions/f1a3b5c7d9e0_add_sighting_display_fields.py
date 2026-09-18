"""add display_meta, seen_count, last_seen_at to shadow_ai_sightings

Revision ID: f1a3b5c7d9e0
Revises: e0f2a4b6c8da
Create Date: 2026-09-18 06:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "f1a3b5c7d9e0"
down_revision: Union[str, None] = "e0f2a4b6c8da"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "shadow_ai_sightings", sa.Column("display_meta", postgresql.JSONB(), nullable=True)
    )
    op.add_column(
        "shadow_ai_sightings",
        sa.Column("seen_count", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "shadow_ai_sightings",
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Backfill last_seen_at from created_at for rows that predate this
    # column, so the UI's "last seen" never shows blank for old sightings.
    op.execute("UPDATE shadow_ai_sightings SET last_seen_at = created_at WHERE last_seen_at IS NULL")


def downgrade() -> None:
    op.drop_column("shadow_ai_sightings", "last_seen_at")
    op.drop_column("shadow_ai_sightings", "seen_count")
    op.drop_column("shadow_ai_sightings", "display_meta")
