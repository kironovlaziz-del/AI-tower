"""create datasets table

Revision ID: e5f0a2b3c4d9
Revises: d4e9f1a2b3c8
Create Date: 2026-09-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f0a2b3c4d9'
down_revision: Union[str, None] = 'd4e9f1a2b3c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'datasets',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('org_id', sa.Integer(), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('task_type', sa.String(length=50), nullable=True, server_default='other'),
        sa.Column('file_format', sa.String(length=20), nullable=True),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('size_bytes', sa.BigInteger(), nullable=True, server_default='0'),
        sa.Column('uploaded_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.create_index('ix_datasets_org_id', 'datasets', ['org_id'])


def downgrade() -> None:
    op.drop_index('ix_datasets_org_id', table_name='datasets')
    op.drop_table('datasets')
