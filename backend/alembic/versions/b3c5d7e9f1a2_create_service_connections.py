"""create service_connections table

Revision ID: b3c5d7e9f1a2
Revises: a2b4c6d8e0f1
Create Date: 2026-09-19 09:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "b3c5d7e9f1a2"
down_revision: Union[str, None] = "a2b4c6d8e0f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "service_connections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column(
            "discovered_service_id",
            sa.Integer(),
            sa.ForeignKey("discovered_services.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("service_type", sa.String(length=50), nullable=False),
        sa.Column("host", sa.String(length=255), nullable=False),
        sa.Column("port", sa.Integer(), nullable=True),
        sa.Column("bind_dn", sa.String(length=500), nullable=True),
        sa.Column("base_dn", sa.String(length=500), nullable=True),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("bind_password_encrypted", sa.Text(), nullable=True),
        sa.Column("info", postgresql.JSONB(), nullable=True),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(length=500), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_service_connections_id", "service_connections", ["id"])
    op.create_index("ix_service_connections_org_id", "service_connections", ["org_id"])
    op.create_index(
        "ix_service_connections_discovered_service_id",
        "service_connections",
        ["discovered_service_id"],
    )


def downgrade() -> None:
    op.drop_table("service_connections")
