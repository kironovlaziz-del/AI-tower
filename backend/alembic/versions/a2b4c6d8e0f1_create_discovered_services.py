"""create discovered_services table

Revision ID: a2b4c6d8e0f1
Revises: f1a3b5c7d9e0
Create Date: 2026-09-18 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "a2b4c6d8e0f1"
down_revision: Union[str, None] = "f1a3b5c7d9e0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "discovered_services",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("service_type", sa.String(length=50), nullable=False),
        sa.Column("host", sa.String(length=255), nullable=False),
        sa.Column("port", sa.Integer(), nullable=True),
        sa.Column("discovered_via", sa.String(length=50), nullable=False),
        sa.Column("details", postgresql.JSONB(), nullable=True),
        sa.Column(
            "connect_status", sa.String(length=30), nullable=False, server_default="discovered"
        ),
        sa.Column("connect_error", sa.String(length=500), nullable=True),
        sa.Column("connected_ref_type", sa.String(length=50), nullable=True),
        sa.Column("connected_ref_id", sa.Integer(), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("connected_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_discovered_services_id", "discovered_services", ["id"])
    op.create_index("ix_discovered_services_org_id", "discovered_services", ["org_id"])
    # The dedup key report_services relies on: re-discovering the same
    # service on the same host updates in place instead of duplicating.
    op.create_unique_constraint(
        "uq_discovered_service_org_type_host",
        "discovered_services",
        ["org_id", "service_type", "host"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_discovered_service_org_type_host", "discovered_services", type_="unique"
    )
    op.drop_table("discovered_services")
