"""create ai_overrides table

Revision ID: c7d8e2f4a1b6
Revises: a3e7f0c1b9d2
Create Date: 2026-09-05 00:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = 'c7d8e2f4a1b6'
down_revision: Union[str, None] = 'a3e7f0c1b9d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ai_overrides',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('request_id', sa.Integer(), sa.ForeignKey('ai_requests.id'), nullable=False),
        sa.Column('override_type', sa.String(length=20), nullable=False),
        sa.Column('override_payload_json', JSONB, nullable=True),
        sa.Column('operator_user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.create_index('ix_ai_overrides_request_id', 'ai_overrides', ['request_id'])


def downgrade() -> None:
    op.drop_index('ix_ai_overrides_request_id', table_name='ai_overrides')
    op.drop_table('ai_overrides')
