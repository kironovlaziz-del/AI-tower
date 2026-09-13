"""create prediction_logs

Revision ID: c4d5e6f7a8b9
Revises: b2c3d4e5f6a7
Create Date: 2026-09-13 08:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "prediction_logs",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "org_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False
        ),
        sa.Column(
            "deployment_id",
            sa.Integer(),
            sa.ForeignKey("model_deployments.id"),
            nullable=False,
        ),
        sa.Column("features_json", JSONB, nullable=True),
        sa.Column("prediction", sa.String(length=255), nullable=True),
        sa.Column("feedback", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_prediction_logs_org_id", "prediction_logs", ["org_id"])
    op.create_index(
        "ix_prediction_logs_deployment_id", "prediction_logs", ["deployment_id"]
    )
    op.create_index(
        "ix_prediction_logs_created_at", "prediction_logs", ["created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_prediction_logs_created_at", table_name="prediction_logs")
    op.drop_index("ix_prediction_logs_deployment_id", table_name="prediction_logs")
    op.drop_index("ix_prediction_logs_org_id", table_name="prediction_logs")
    op.drop_table("prediction_logs")
