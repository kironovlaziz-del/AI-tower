from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.core.database import get_db
from app.core.pagination import PaginationParams
from app.schemas.audit_log import AuditLogOut
from app.schemas.pagination import Page
from app.services.audit_service import AuditService
from app.models.user import User
from app.api.deps import get_current_user

router = APIRouter()


@router.get("/", response_model=Page[AuditLogOut])
async def list_audit_logs(
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    actor_user_id: Optional[int] = None,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = AuditService(db)
    items = await service.list_logs(
        current_user.org_id,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_user_id=actor_user_id,
        skip=pagination.skip,
        limit=pagination.limit,
    )
    # Audit service returns only items (no total) - count is expensive on
    # large logs, so we return len(items) as the visible-total. A dedicated
    # count endpoint can be added later if needed.
    return Page(
        items=items,
        total=len(items),
        skip=pagination.skip,
        limit=pagination.limit,
    )
