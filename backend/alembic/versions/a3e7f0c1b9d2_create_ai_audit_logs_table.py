"""create ai_audit_logs table

Revision ID: a3e7f0c1b9d2
Revises: f1a2c9d4e8b7
Create Date: 2026-09-05 00:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = 'a3e7f0c1b9d2'
down_revision: Union[str, None] = 'f1a2c9d4e8b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ai_audit_logs',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('org_id', sa.Integer(), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('actor_user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('metadata_json', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.create_index('ix_ai_audit_logs_org_id', 'ai_audit_logs', ['org_id'])
    op.create_index('ix_ai_audit_logs_entity_type', 'ai_audit_logs', ['entity_type'])
    op.create_index('ix_ai_audit_logs_entity_id', 'ai_audit_logs', ['entity_id'])


def downgrade() -> None:
    op.drop_index('ix_ai_audit_logs_entity_id', table_name='ai_audit_logs')
    op.drop_index('ix_ai_audit_logs_entity_type', table_name='ai_audit_logs')
    op.drop_index('ix_ai_audit_logs_org_id', table_name='ai_audit_logs')
    op.drop_table('ai_audit_logs')
