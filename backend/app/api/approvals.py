from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.core.database import get_db
from app.schemas.approval import ApprovalCreate, ApprovalDecision, ApprovalOut
from app.services.approval_service import ApprovalService
from app.services.audit_service import AuditService
from app.services import notification_service
from app.models.user import User
from app.api.deps import get_current_user, require_role
from app.models.user import UserRole

router = APIRouter()

@router.post("/", response_model=ApprovalOut)
async def create_approval(
    data: ApprovalCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.approver))
):
    service = ApprovalService(db)
    approval = await service.create_approval(current_user.org_id, data)
    await AuditService(db).log(
        current_user.org_id, current_user.id, "approval", approval.id, "created",
        {"request_id": approval.request_id, "approver_user_id": approval.approver_user_id},
    )
    await notification_service.notify(
        db, current_user.org_id, "approval_pending",
        "Требуется согласование запроса",
        f"Запрос #{approval.request_id} ожидает согласования.",
        {"request_id": approval.request_id, "approval_id": approval.id},
    )
    return approval

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
    current_user: User = Depends(require_role(UserRole.admin, UserRole.approver))
):
    service = ApprovalService(db)
    approval = await service.make_decision(approval_id, current_user.org_id, data)
    await AuditService(db).log(
        current_user.org_id, current_user.id, "approval", approval.id, data.decision,
        {"request_id": approval.request_id, "reason": data.reason},
    )
    return approval
