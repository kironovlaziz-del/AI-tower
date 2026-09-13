"""create model_deployments

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-09-13 06:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "model_deployments",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "org_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False
        ),
        sa.Column(
            "training_job_id",
            sa.Integer(),
            sa.ForeignKey("training_jobs.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="active"
        ),
        sa.Column(
            "traffic_weight", sa.Float(), nullable=False, server_default="1.0"
        ),
        sa.Column(
            "created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "org_id",
            "name",
            "version",
            name="uq_model_deployments_org_name_version",
        ),
    )
    op.create_index(
        "ix_model_deployments_org_id", "model_deployments", ["org_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_model_deployments_org_id", table_name="model_deployments")
    op.drop_table("model_deployments")
