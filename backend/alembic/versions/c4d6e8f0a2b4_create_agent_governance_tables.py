"""create agent governance tables

Revision ID: c4d6e8f0a2b4
Revises: b3c5d7e9f1a2
Create Date: 2026-09-19 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c4d6e8f0a2b4"
down_revision: Union[str, None] = "b3c5d7e9f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("agent_type", sa.String(length=50), nullable=True),
        sa.Column("version", sa.String(length=50), nullable=True),
        sa.Column("owner_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("owner_team", sa.String(length=100), nullable=True),
        sa.Column("capabilities", postgresql.JSONB(), nullable=True),
        sa.Column("allowed_tools", postgresql.JSONB(), nullable=True),
        sa.Column("allowed_models", postgresql.JSONB(), nullable=True),
        sa.Column("max_delegation_depth", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("api_key_hash", sa.String(length=64), nullable=False),
        sa.Column("public_key", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_agents_id", "agents", ["id"])
    op.create_index("ix_agents_org_id", "agents", ["org_id"])
    op.create_unique_constraint("uq_agents_api_key_hash", "agents", ["api_key_hash"])

    op.create_table(
        "agent_policies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("agent_id", sa.Integer(), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("rules", postgresql.JSONB(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_agent_policies_id", "agent_policies", ["id"])
    op.create_index("ix_agent_policies_org_id", "agent_policies", ["org_id"])

    op.create_table(
        "delegation_chains",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("root_agent_id", sa.Integer(), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("root_task", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("total_hops", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_depth_reached", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_delegation_chains_id", "delegation_chains", ["id"])
    op.create_index("ix_delegation_chains_org_id", "delegation_chains", ["org_id"])
    op.create_index("ix_delegation_chains_root_agent_id", "delegation_chains", ["root_agent_id"])

    op.create_table(
        "delegation_hops",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("chain_id", sa.Integer(), sa.ForeignKey("delegation_chains.id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_agent_id", sa.Integer(), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("to_agent_id", sa.Integer(), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("depth", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("delegated_capabilities", postgresql.JSONB(), nullable=True),
        sa.Column("task_description", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("signature", sa.Text(), nullable=True),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_delegation_hops_id", "delegation_hops", ["id"])
    op.create_index("ix_delegation_hops_org_id", "delegation_hops", ["org_id"])
    op.create_index("ix_delegation_hops_chain_id", "delegation_hops", ["chain_id"])

    op.create_table(
        "agent_actions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("chain_id", sa.Integer(), sa.ForeignKey("delegation_chains.id", ondelete="CASCADE"), nullable=True),
        sa.Column("agent_id", sa.Integer(), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("action_type", sa.String(length=50), nullable=True),
        sa.Column("tool_name", sa.String(length=100), nullable=True),
        sa.Column("input_data", postgresql.JSONB(), nullable=True),
        sa.Column("output_data", postgresql.JSONB(), nullable=True),
        sa.Column("policy_check_result", sa.String(length=20), nullable=True),
        sa.Column("policy_id", sa.Integer(), sa.ForeignKey("agent_policies.id"), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("signature", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_agent_actions_id", "agent_actions", ["id"])
    op.create_index("ix_agent_actions_org_id", "agent_actions", ["org_id"])
    op.create_index("ix_agent_actions_chain_id", "agent_actions", ["chain_id"])
    op.create_index("ix_agent_actions_agent_id", "agent_actions", ["agent_id"])
    op.create_index("ix_agent_actions_created_at", "agent_actions", ["created_at"])

    op.create_table(
        "agent_incidents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("chain_id", sa.Integer(), sa.ForeignKey("delegation_chains.id", ondelete="CASCADE"), nullable=True),
        sa.Column("agent_id", sa.Integer(), sa.ForeignKey("agents.id"), nullable=True),
        sa.Column("incident_type", sa.String(length=50), nullable=True),
        sa.Column("severity", sa.String(length=20), nullable=True),
        sa.Column("details", postgresql.JSONB(), nullable=True),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_agent_incidents_id", "agent_incidents", ["id"])
    op.create_index("ix_agent_incidents_org_id", "agent_incidents", ["org_id"])
    op.create_index("ix_agent_incidents_chain_id", "agent_incidents", ["chain_id"])
    op.create_index("ix_agent_incidents_agent_id", "agent_incidents", ["agent_id"])


def downgrade() -> None:
    op.drop_table("agent_incidents")
    op.drop_table("agent_actions")
    op.drop_table("delegation_hops")
    op.drop_table("delegation_chains")
    op.drop_table("agent_policies")
    op.drop_table("agents")
