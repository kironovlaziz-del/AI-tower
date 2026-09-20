from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.pagination import PaginationParams
from app.core.agent_signing import verify_payload
from app.schemas.pagination import Page
from app.schemas.agent import (
    AgentCreate, AgentUpdate, AgentOut, AgentCreated,
    AgentKillRequest, AgentKillResponse,
    DelegateRequest, DelegateResponse, ChainOut, ChainDetail, HopOut,
    ActionCheckRequest, ActionCheckResponse, ActionRecordRequest, ActionDenyRequest, ActionOut,
    AgentPolicyCreate, AgentPolicyOut, AgentIncidentOut,
    GovernanceGraph,
)
from app.services.agent_registry import AgentRegistry
from app.services.delegation_service import DelegationService
from app.services.agent_audit import AgentAudit
from app.services.governance_graph_service import GovernanceGraphService
from app.services.audit_service import AuditService
from app.models.agent import Agent, AgentPolicy
from app.models.agent_action import AgentIncident
from app.models.user import User, UserRole
from app.api.deps import get_current_user, require_role

router = APIRouter()


# ============================ Agents ============================

@router.post("/register", response_model=AgentCreated)
async def register_agent(
    data: AgentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    registry = AgentRegistry(db)
    agent, raw_key, private_key = await registry.register(current_user.org_id, current_user.id, data)
    await AuditService(db).log(
        current_user.org_id, current_user.id, "agent", agent.id, "registered",
        {"name": agent.name, "agent_type": agent.agent_type},
    )
    return AgentCreated(
        **AgentOut.model_validate(agent).model_dump(),
        api_key=raw_key,
        private_key=private_key,
    )


@router.get("/graph", response_model=GovernanceGraph)
async def governance_graph(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    The live governance map in one query: agents (nodes) with status,
    violation, and recent-activity annotations; delegation hops (edges)
    with verification and violation state. Polled by the graph UI.
    """
    graph = await GovernanceGraphService(db).build(current_user.org_id)
    return graph


@router.get("/", response_model=Page[AgentOut])
async def list_agents(
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    registry = AgentRegistry(db)
    items, total = await registry.list_agents(current_user.org_id, pagination.skip, pagination.limit)
    return Page(items=items, total=total, skip=pagination.skip, limit=pagination.limit)


@router.get("/{agent_id}", response_model=AgentOut)
async def get_agent(
    agent_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await AgentRegistry(db).get_agent(agent_id, current_user.org_id)


@router.put("/{agent_id}", response_model=AgentOut)
async def update_agent(
    agent_id: int,
    data: AgentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    agent = await AgentRegistry(db).update_agent(agent_id, current_user.org_id, data)
    await AuditService(db).log(
        current_user.org_id, current_user.id, "agent", agent_id, "updated",
        data.model_dump(exclude_unset=True),
    )
    return agent


@router.post("/{agent_id}/kill", response_model=AgentKillResponse)
async def kill_agent(
    agent_id: int,
    data: AgentKillRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    stopped, terminated = await AgentRegistry(db).kill_agent(
        agent_id, current_user.org_id, data.reason, data.cascade
    )
    await AuditService(db).log(
        current_user.org_id, current_user.id, "agent", agent_id, "killed",
        {"reason": data.reason, "cascade": data.cascade, "chains_terminated": terminated},
    )
    return AgentKillResponse(agents_stopped=stopped, chains_terminated=terminated)


# ========================= Delegation =========================

@router.post("/{agent_id}/delegate", response_model=DelegateResponse)
async def delegate(
    agent_id: int,
    data: DelegateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Record a delegation from `agent_id` to `to_agent_id`. If a signature
    is supplied, it is verified against the delegating agent's public key
    over the canonical delegation payload; an invalid signature is
    rejected before any chain state changes.
    """
    service = DelegationService(db)
    registry = AgentRegistry(db)

    # Verify signature (if provided) against the delegating agent's key.
    verified = False
    if data.signature:
        from_agent = await registry.get_agent(agent_id, current_user.org_id)
        payload = {
            "from_agent_id": agent_id,
            "to_agent_id": data.to_agent_id,
            "task": data.task,
            "delegated_capabilities": sorted(data.delegated_capabilities or []),
            "chain_id": data.chain_id,
        }
        verified = verify_payload(payload, data.signature, from_agent.public_key or "")
        if not verified:
            from fastapi import HTTPException, status as st
            raise HTTPException(
                status_code=st.HTTP_400_BAD_REQUEST,
                detail="Invalid delegation signature",
            )

    expires_at = None
    if data.expires_in:
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=data.expires_in)

    chain, hop = await service.delegate(
        org_id=current_user.org_id,
        from_agent_id=agent_id,
        to_agent_id=data.to_agent_id,
        task=data.task,
        delegated_capabilities=data.delegated_capabilities or [],
        signature=data.signature,
        chain_id=data.chain_id,
        expires_at=expires_at,
    )
    from_agent = await registry.get_agent(agent_id, current_user.org_id)
    remaining = max(from_agent.max_delegation_depth - hop.depth, 0)
    return DelegateResponse(
        chain_id=chain.id, hop_id=hop.id, depth=hop.depth,
        max_depth_remaining=remaining, verified=verified,
    )


@router.get("/delegation-chains/", response_model=Page[ChainOut])
async def list_chains(
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = await DelegationService(db).list_chains(
        current_user.org_id, pagination.skip, pagination.limit
    )
    return Page(items=items, total=total, skip=pagination.skip, limit=pagination.limit)


@router.get("/delegation-chains/{chain_id}", response_model=ChainDetail)
async def get_chain(
    chain_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    detail = await DelegationService(db).get_chain_detail(chain_id, current_user.org_id)
    chain = detail["chain"]
    return ChainDetail(
        **ChainOut.model_validate(chain).model_dump(),
        hops=[HopOut.model_validate(h) for h in detail["hops"]],
    )


# ========================== Actions ==========================

@router.post("/actions/check", response_model=ActionCheckResponse)
async def check_action_endpoint(
    data: ActionCheckRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    decision = await AgentAudit(db).check(
        org_id=current_user.org_id,
        agent_id=data.agent_id,
        chain_id=data.chain_id,
        action_type=data.action_type,
        tool_name=data.tool_name,
        input_data=data.input,
        action_capabilities=data.action_capabilities,
    )
    return ActionCheckResponse(
        decision=decision.result, reason=decision.reason,
        incident_type=decision.incident_type, policy_id=decision.matched_policy_id,
    )


@router.post("/actions/record", response_model=ActionOut)
async def record_action_endpoint(
    data: ActionRecordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Check the action against policy AND persist it in one call, so a
    recorded action always carries its policy verdict and a denial always
    produces an incident. (A caller that only wants the verdict without
    recording uses /actions/check.)
    """
    audit = AgentAudit(db)
    decision = await audit.check(
        org_id=current_user.org_id,
        agent_id=data.agent_id,
        chain_id=data.chain_id,
        action_type=data.action_type,
        tool_name=data.tool_name,
        input_data=data.input,
        action_capabilities=[],
    )
    action = await audit.record(
        org_id=current_user.org_id,
        agent_id=data.agent_id,
        chain_id=data.chain_id,
        action_type=data.action_type,
        tool_name=data.tool_name,
        input_data=data.input,
        output_data=data.output,
        signature=data.signature,
        duration_ms=data.duration_ms,
        decision=decision,
    )
    return action


@router.get("/actions/", response_model=Page[ActionOut])
async def list_actions(
    chain_id: Optional[int] = None,
    agent_id: Optional[int] = None,
    result: Optional[str] = None,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = await AgentAudit(db).list_actions(
        current_user.org_id, chain_id, agent_id, result, pagination.skip, pagination.limit
    )
    return Page(items=items, total=total, skip=pagination.skip, limit=pagination.limit)


@router.post("/actions/{action_id}/approve", response_model=ActionOut)
async def approve_action(
    action_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.approver)),
):
    action = await AgentAudit(db).approve_action(action_id, current_user.org_id)
    await AuditService(db).log(
        current_user.org_id, current_user.id, "agent_action", action_id, "approved",
        {"tool": action.tool_name},
    )
    return action


@router.post("/actions/{action_id}/deny", response_model=ActionOut)
async def deny_action(
    action_id: int,
    data: ActionDenyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.approver)),
):
    action = await AgentAudit(db).deny_action(action_id, current_user.org_id, data.reason)
    await AuditService(db).log(
        current_user.org_id, current_user.id, "agent_action", action_id, "denied",
        {"tool": action.tool_name, "reason": data.reason},
    )
    return action


# ========================= Agent policies =========================

@router.post("/policies/", response_model=AgentPolicyOut)
async def create_agent_policy(
    data: AgentPolicyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    policy = AgentPolicy(
        org_id=current_user.org_id,
        agent_id=data.agent_id,
        name=data.name,
        rules=data.rules,
        priority=data.priority,
        enabled=data.enabled,
        created_by=current_user.id,
    )
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    await AuditService(db).log(
        current_user.org_id, current_user.id, "agent_policy", policy.id, "created",
        {"name": policy.name, "agent_id": policy.agent_id},
    )
    return policy


@router.get("/policies/", response_model=Page[AgentPolicyOut])
async def list_agent_policies(
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import func as sqlfunc
    base = select(AgentPolicy).where(AgentPolicy.org_id == current_user.org_id)
    total = await db.scalar(select(sqlfunc.count()).select_from(base.subquery()))
    result = await db.execute(
        base.order_by(AgentPolicy.priority.desc()).offset(pagination.skip).limit(pagination.limit)
    )
    return Page(items=list(result.scalars().all()), total=int(total or 0),
                skip=pagination.skip, limit=pagination.limit)


# ========================== Incidents ==========================

@router.get("/incidents/", response_model=Page[AgentIncidentOut])
async def list_agent_incidents(
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import func as sqlfunc
    base = select(AgentIncident).where(AgentIncident.org_id == current_user.org_id)
    total = await db.scalar(select(sqlfunc.count()).select_from(base.subquery()))
    result = await db.execute(
        base.order_by(AgentIncident.created_at.desc()).offset(pagination.skip).limit(pagination.limit)
    )
    return Page(items=list(result.scalars().all()), total=int(total or 0),
                skip=pagination.skip, limit=pagination.limit)
