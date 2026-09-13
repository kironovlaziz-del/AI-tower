"""unique constraint on notification_channels (org_id, channel_type, target)

Revision ID: a1b2c3d4e5f6
Revises: f8a9b0c1d2e3
Create Date: 2026-09-13 05:00:00.000000

Two identical channels (same org, same type, same target) would deliver
the same event twice. Enforce uniqueness at the DB level so the invariant
holds even if a race slips past the application-level check.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "f8a9b0c1d2e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Clean up existing duplicates before adding the constraint: keep the
    # oldest row per (org_id, channel_type, target) and delete the rest.
    op.execute(
        """
        DELETE FROM notification_channels nc
        USING notification_channels older
        WHERE nc.org_id = older.org_id
          AND nc.channel_type = older.channel_type
          AND nc.target = older.target
          AND nc.id > older.id
        """
    )
    op.create_unique_constraint(
        "uq_notification_channels_org_type_target",
        "notification_channels",
        ["org_id", "channel_type", "target"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_notification_channels_org_type_target",
        "notification_channels",
        type_="unique",
    )
