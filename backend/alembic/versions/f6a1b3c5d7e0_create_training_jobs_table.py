"""create training_jobs table

Revision ID: f6a1b3c5d7e0
Revises: e5f0a2b3c4d9
Create Date: 2026-09-06 00:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = 'f6a1b3c5d7e0'
down_revision: Union[str, None] = 'e5f0a2b3c4d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'training_jobs',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('org_id', sa.Integer(), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('dataset_id', sa.Integer(), sa.ForeignKey('datasets.id'), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('task_type', sa.String(length=30), nullable=False),
        sa.Column('target_column', sa.String(length=255), nullable=False),
        sa.Column('algorithm', sa.String(length=50), nullable=False),
        sa.Column('hyperparameters_json', JSONB, nullable=True),
        sa.Column('feature_columns_json', JSONB, nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True, server_default='queued'),
        sa.Column('metrics_json', JSONB, nullable=True),
        sa.Column('model_path', sa.String(length=500), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_training_jobs_org_id', 'training_jobs', ['org_id'])


def downgrade() -> None:
    op.drop_index('ix_training_jobs_org_id', table_name='training_jobs')
    op.drop_table('training_jobs')
