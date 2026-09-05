from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.core.database import get_db
from app.schemas.policy import PolicyCreate, PolicyOut, PolicyVersionCreate, PolicyVersionOut
from app.services.policy_service import PolicyService
from app.models.user import User
from app.api.deps import get_current_user

router = APIRouter()

@router.post("/", response_model=PolicyOut)
async def create_policy(
    policy_data: PolicyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = PolicyService(db)
    return await service.create_policy(current_user.org_id, policy_data, current_user.id)

@router.get("/", response_model=List[PolicyOut])
async def list_policies(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = PolicyService(db)
    return await service.list_policies(current_user.org_id)

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
    current_user: User = Depends(get_current_user)
):
    service = PolicyService(db)
    return await service.create_policy_version(
        policy_id, current_user.org_id, version_data, current_user.id
    )

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
    current_user: User = Depends(get_current_user)
):
    service = PolicyService(db)
    return await service.approve_policy_version(
        policy_id, version_id, current_user.org_id, current_user.id
    )
