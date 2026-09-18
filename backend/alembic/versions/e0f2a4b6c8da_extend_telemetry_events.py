"""extend telemetry events for process/network/file collector types

Revision ID: e0f2a4b6c8da
Revises: d9e1f3a5b7c9
Create Date: 2026-09-17 15:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e0f2a4b6c8da"
down_revision: Union[str, None] = "d9e1f3a5b7c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # detected_via ("network_proxy"/"endpoint"/"browser_extension") described
    # the *collector type*, which is redundant with ingestion_sources.source_type
    # (known from the authenticating API key already) - event_type instead
    # describes *what kind of signal this is* (domain_visit, process_detected,
    # network_conn, local_model_found), which is the dimension the real
    # agent/extension wire format actually needs.
    op.alter_column(
        "ai_telemetry_events", "detected_via", new_column_name="event_type"
    )
    op.add_column("ai_telemetry_events", sa.Column("agent_id", sa.String(length=255), nullable=True))
    op.add_column("ai_telemetry_events", sa.Column("risk_score", sa.Float(), nullable=True))
    op.add_column("ai_telemetry_events", sa.Column("action_taken", sa.String(length=50), nullable=True))
    # Local-signal events (process/network/file) have no real domain to
    # classify - only a fixed placeholder for display - and never get a
    # policy_status, since there is no domain-catalog concept for them.
    op.alter_column("ai_telemetry_events", "domain", nullable=True)
    op.alter_column("ai_telemetry_events", "matched_policy_status", nullable=True)


def downgrade() -> None:
    op.alter_column("ai_telemetry_events", "matched_policy_status", nullable=False)
    op.alter_column("ai_telemetry_events", "domain", nullable=False)
    op.drop_column("ai_telemetry_events", "action_taken")
    op.drop_column("ai_telemetry_events", "risk_score")
    op.drop_column("ai_telemetry_events", "agent_id")
    op.alter_column(
        "ai_telemetry_events", "event_type", new_column_name="detected_via"
    )
