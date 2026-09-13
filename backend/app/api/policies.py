from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.core.database import get_db
from app.core.pagination import PaginationParams
from app.schemas.policy import PolicyCreate, PolicyOut, PolicyVersionCreate, PolicyVersionOut
from app.schemas.pagination import Page
from app.services.policy_service import PolicyService
from app.services.audit_service import AuditService
from app.models.user import User
from app.api.deps import get_current_user, require_role
from app.models.user import UserRole

router = APIRouter()

@router.post("/", response_model=PolicyOut)
async def create_policy(
    policy_data: PolicyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin))
):
    service = PolicyService(db)
    policy = await service.create_policy(current_user.org_id, policy_data, current_user.id)
    await AuditService(db).log(
        current_user.org_id, current_user.id, "policy", policy.id, "created",
        {"name": policy.name},
    )
    return policy

@router.get("/", response_model=Page[PolicyOut])
async def list_policies(
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = PolicyService(db)
    items, total = await service.list_policies(
        current_user.org_id, skip=pagination.skip, limit=pagination.limit
    )
    return Page(items=items, total=total, skip=pagination.skip, limit=pagination.limit)

@router.get("/{policy_id}", response_model=PolicyOut)
async def get_policy(
    policy_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = PolicyService(db)
    return await service.get_policy(policy_id, current_user.org_id)

@router.post("/{policy_id}/versions", response_model=PolicyVersionOut)
async def create_policy_version(
    policy_id: int,
    version_data: PolicyVersionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin))
):
    service = PolicyService(db)
    version = await service.create_policy_version(
        policy_id, current_user.org_id, version_data, current_user.id
    )
    await AuditService(db).log(
        current_user.org_id, current_user.id, "policy_version", version.id, "created",
        {"policy_id": policy_id, "version": version.version, "rules_json": version.rules_json},
    )
    return version

@router.get("/{policy_id}/versions", response_model=List[PolicyVersionOut])
async def get_policy_versions(
    policy_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = PolicyService(db)
    return await service.get_policy_versions(policy_id, current_user.org_id)

@router.post("/{policy_id}/versions/{version_id}/approve", response_model=PolicyVersionOut)
async def approve_policy_version(
    policy_id: int,
    version_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.approver))
):
    service = PolicyService(db)
    version = await service.approve_policy_version(
        policy_id, version_id, current_user.org_id, current_user.id
    )
    await AuditService(db).log(
        current_user.org_id, current_user.id, "policy_version", version.id, "approved",
        {"policy_id": policy_id, "version": version.version},
    )
    return version
