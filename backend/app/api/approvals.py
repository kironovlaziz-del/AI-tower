from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.core.database import get_db
from app.schemas.approval import ApprovalCreate, ApprovalDecision, ApprovalOut
from app.services.approval_service import ApprovalService
from app.models.user import User
from app.api.deps import get_current_user

router = APIRouter()

@router.post("/", response_model=ApprovalOut)
async def create_approval(
    data: ApprovalCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = ApprovalService(db)
    return await service.create_approval(current_user.org_id, data)

@router.get("/", response_model=List[ApprovalOut])
async def list_approvals(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = ApprovalService(db)
    return await service.list_approvals(current_user.org_id)

@router.post("/{approval_id}/decision", response_model=ApprovalOut)
async def make_decision(
    approval_id: int,
    data: ApprovalDecision,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = ApprovalService(db)
    return await service.make_decision(approval_id, current_user.org_id, data)
