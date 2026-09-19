from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent, AgentPolicy
from app.models.delegation import DelegationChain, DelegationHop
from app.models.agent_action import AgentAction, AgentIncident
from app.services.agent_policy_engine import (
    check_action,
    AgentView,
    ChainView,
    ActionContext,
    ALLOWED,
    DENIED,
)


class AgentAudit:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_agent(self, agent_id: int, org_id: int) -> Agent:
        result = await self.db.execute(
            select(Agent).where(Agent.id == agent_id, Agent.org_id == org_id)
        )
        agent = result.scalar_one_or_none()
        if not agent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
        return agent

    async def _chain_view(self, chain_id: Optional[int], agent_id: int, agent: Agent) -> ChainView:
        if chain_id is None:
            return ChainView(max_depth_reached=0, granted_capabilities=list(agent.capabilities or []))
        result = await self.db.execute(
            select(DelegationChain).where(DelegationChain.id == chain_id)
        )
        chain = result.scalar_one_or_none()
        if not chain:
            return ChainView(max_depth_reached=0, granted_capabilities=list(agent.capabilities or []))
        # capabilities granted to this agent within the chain
        hop_result = await self.db.execute(
            select(DelegationHop)
            .where(DelegationHop.chain_id == chain_id, DelegationHop.to_agent_id == agent_id)
            .order_by(DelegationHop.depth.desc())
        )
        hop = hop_result.scalars().first()
        granted = (
            list(hop.delegated_capabilities)
            if hop and hop.delegated_capabilities is not None
            else list(agent.capabilities or [])
        )
        return ChainView(max_depth_reached=chain.max_depth_reached or 0, granted_capabilities=granted)

    async def _custom_policies(self, org_id: int, agent_id: int) -> List[dict]:
        """Enabled agent policies that apply: those scoped to this agent
        plus org-wide ones (agent_id IS NULL), highest priority first."""
        result = await self.db.execute(
            select(AgentPolicy).where(
                AgentPolicy.org_id == org_id,
                AgentPolicy.enabled == True,  # noqa: E712
                ((AgentPolicy.agent_id == agent_id) | (AgentPolicy.agent_id.is_(None))),
            ).order_by(AgentPolicy.priority.desc())
        )
        return [
            {"id": p.id, "name": p.name, "rules": p.rules or {}}
            for p in result.scalars().all()
        ]

    async def check(
        self,
        org_id: int,
        agent_id: int,
        chain_id: Optional[int],
        action_type: Optional[str],
        tool_name: Optional[str],
        input_data: dict,
        action_capabilities: List[str],
    ):
        """Run the policy engine for a proposed action. Returns the
        Decision (does not persist - use record() for that)."""
        agent = await self._get_agent(agent_id, org_id)
        agent_view = AgentView(
            allowed_tools=list(agent.allowed_tools or []),
            allowed_models=list(agent.allowed_models or []),
            max_delegation_depth=agent.max_delegation_depth,
            status=agent.status,
        )
        chain_view = await self._chain_view(chain_id, agent_id, agent)
        ctx = ActionContext(
            tool_name=tool_name,
            action_type=action_type,
            input_data=input_data or {},
            action_capabilities=action_capabilities or [],
        )
        policies = await self._custom_policies(org_id, agent_id)
        return check_action(agent_view, chain_view, ctx, policies)

    async def record(
        self,
        org_id: int,
        agent_id: int,
        chain_id: Optional[int],
        action_type: Optional[str],
        tool_name: Optional[str],
        input_data: dict,
        output_data: Optional[dict],
        signature: Optional[str],
        duration_ms: Optional[int],
        decision=None,
    ) -> AgentAction:
        """
        Persist an action row. If a Decision is supplied, its verdict and
        reason are stored, and a denial with an incident_type also raises
        an AgentIncident. Recording happens for denied actions too - the
        record of what an agent TRIED is the whole point.
        """
        action = AgentAction(
            org_id=org_id,
            agent_id=agent_id,
            chain_id=chain_id,
            action_type=action_type,
            tool_name=tool_name,
            input_data=input_data,
            output_data=output_data,
            policy_check_result=decision.result if decision else None,
            policy_id=decision.matched_policy_id if decision else None,
            reason=decision.reason if decision else None,
            signature=signature,
            duration_ms=duration_ms,
        )
        self.db.add(action)

        if decision and decision.result == DENIED and decision.incident_type:
            self.db.add(
                AgentIncident(
                    org_id=org_id,
                    chain_id=chain_id,
                    agent_id=agent_id,
                    incident_type=decision.incident_type,
                    severity="high" if decision.incident_type == "depth_exceeded" else "critical",
                    details={"tool": tool_name, "reason": decision.reason},
                )
            )

        await self.db.commit()
        await self.db.refresh(action)
        return action

    async def list_actions(
        self, org_id: int, chain_id: Optional[int] = None, agent_id: Optional[int] = None,
        skip: int = 0, limit: int = 50,
    ) -> Tuple[List[AgentAction], int]:
        from sqlalchemy import func as sqlfunc
        base = select(AgentAction).where(AgentAction.org_id == org_id)
        if chain_id is not None:
            base = base.where(AgentAction.chain_id == chain_id)
        if agent_id is not None:
            base = base.where(AgentAction.agent_id == agent_id)
        total = await self.db.scalar(select(sqlfunc.count()).select_from(base.subquery()))
        result = await self.db.execute(
            base.order_by(AgentAction.created_at.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().all()), int(total or 0)
