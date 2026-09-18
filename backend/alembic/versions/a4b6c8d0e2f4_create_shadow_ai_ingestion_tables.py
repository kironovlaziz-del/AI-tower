"""create shadow ai ingestion tables (ingestion_sources, ai_domain_catalog, ai_telemetry_events)

Revision ID: a4b6c8d0e2f4
Revises: c4d5e6f7a8b9
Create Date: 2026-09-14 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "a4b6c8d0e2f4"
down_revision: Union[str, None] = "c4d5e6f7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ingestion_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.String(length=30), nullable=False),
        sa.Column("api_key_hash", sa.String(length=64), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_ingestion_sources_id", "ingestion_sources", ["id"]
    )
    # A unique constraint in Postgres is already backed by a unique
    # B-tree index, so no separate index is needed for lookups by hash.
    op.create_unique_constraint(
        "uq_ingestion_sources_api_key_hash", "ingestion_sources", ["api_key_hash"]
    )

    op.create_table(
        "ai_domain_catalog",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column("tool_name", sa.String(length=255), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("policy_status", sa.String(length=20), nullable=False, server_default="unknown"),
        sa.Column("source", sa.String(length=20), nullable=True, server_default="manual"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_ai_domain_catalog_id", "ai_domain_catalog", ["id"])
    op.create_unique_constraint(
        "uq_domain_catalog_org_domain", "ai_domain_catalog", ["org_id", "domain"]
    )

    op.create_table(
        "ai_telemetry_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column(
            "ingestion_source_id",
            sa.Integer(),
            sa.ForeignKey("ingestion_sources.id"),
            nullable=False,
        ),
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column("detected_via", sa.String(length=50), nullable=False),
        sa.Column("user_hint", sa.String(length=255), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("matched_policy_status", sa.String(length=20), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_ai_telemetry_events_id", "ai_telemetry_events", ["id"])
    # Telemetry is queried heavily by org+domain (dedup checks, matching)
    # and by org+time (future behavioral analysis), so index both now
    # rather than adding them under load later.
    op.create_index(
        "ix_ai_telemetry_events_org_domain", "ai_telemetry_events", ["org_id", "domain"]
    )
    op.create_index(
        "ix_ai_telemetry_events_org_occurred_at",
        "ai_telemetry_events",
        ["org_id", "occurred_at"],
    )


def downgrade() -> None:
    op.drop_table("ai_telemetry_events")
    op.drop_table("ai_domain_catalog")
    op.drop_table("ingestion_sources")
