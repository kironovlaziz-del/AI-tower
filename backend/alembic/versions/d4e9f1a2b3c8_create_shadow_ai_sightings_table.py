"""create shadow_ai_sightings table

Revision ID: d4e9f1a2b3c8
Revises: c7d8e2f4a1b6
Create Date: 2026-09-05 00:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e9f1a2b3c8'
down_revision: Union[str, None] = 'c7d8e2f4a1b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'shadow_ai_sightings',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('org_id', sa.Integer(), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('tool_name', sa.String(length=255), nullable=False),
        sa.Column('domain', sa.String(length=255), nullable=True),
        sa.Column('detected_via', sa.String(length=50), nullable=True, server_default='manual'),
        sa.Column('user_hint', sa.String(length=255), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True, server_default='new'),
        sa.Column('reported_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('registered_provider_id', sa.Integer(), sa.ForeignKey('ai_providers.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_shadow_ai_sightings_org_id', 'shadow_ai_sightings', ['org_id'])


def downgrade() -> None:
    op.drop_index('ix_shadow_ai_sightings_org_id', table_name='shadow_ai_sightings')
    op.drop_table('shadow_ai_sightings')
