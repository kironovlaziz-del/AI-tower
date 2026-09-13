from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.core.database import get_db
from app.core.pagination import PaginationParams
from app.schemas.approval import ApprovalCreate, ApprovalDecision, ApprovalOut
from app.schemas.pagination import Page
from app.services.approval_service import ApprovalService
from app.services.audit_service import AuditService
from app.services import notification_service
from app.models.user import User, UserRole
from app.api.deps import get_current_user, require_role

router = APIRouter()


@router.post("/", response_model=ApprovalOut)
async def create_approval(
    data: ApprovalCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Any authenticated user can submit a request for approval. The approver
    is chosen server-side based on policy or, failing that, an available
    admin/approver in the organization.
    """
    service = ApprovalService(db)
    approval = await service.create_approval(current_user.org_id, current_user.id, data)
    await AuditService(db).log(
        current_user.org_id, current_user.id, "approval", approval.id, "created",
        {"request_id": approval.request_id, "approver_user_id": approval.approver_user_id},
    )
    await notification_service.notify(
        db, current_user.org_id, "approval_pending",
        "Approval required",
        f"Request #{approval.request_id} is awaiting approval.",
        {"request_id": approval.request_id, "approval_id": approval.id},
    )
    return approval


@router.get("/", response_model=Page[ApprovalOut])
async def list_approvals(
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ApprovalService(db)
    items, total = await service.list_approvals(
        current_user.org_id, skip=pagination.skip, limit=pagination.limit
    )
    return Page(items=items, total=total, skip=pagination.skip, limit=pagination.limit)


@router.post("/{approval_id}/decision", response_model=ApprovalOut)
async def make_decision(
    approval_id: int,
    data: ApprovalDecision,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.approver)),
):
    service = ApprovalService(db)
    approval = await service.make_decision(
        approval_id, current_user.org_id, current_user, data
    )
    await AuditService(db).log(
        current_user.org_id, current_user.id, "approval", approval.id, data.decision,
        {"request_id": approval.request_id, "reason": data.reason},
    )
    return approval
