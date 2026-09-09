"""create notification_channels table

Revision ID: c9d4e6f8a0b3
Revises: b8c3d5e7f9a2
Create Date: 2026-09-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = 'c9d4e6f8a0b3'
down_revision: Union[str, None] = 'b8c3d5e7f9a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'notification_channels',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('org_id', sa.Integer(), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('channel_type', sa.String(length=20), nullable=False),
        sa.Column('target', sa.String(length=500), nullable=False),
        sa.Column('events_json', JSONB, nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=True, server_default=sa.text('true')),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.create_index('ix_notification_channels_org_id', 'notification_channels', ['org_id'])


def downgrade() -> None:
    op.drop_index('ix_notification_channels_org_id', table_name='notification_channels')
    op.drop_table('notification_channels')
