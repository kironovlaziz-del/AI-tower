from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.core.database import get_db
from app.schemas.audit_log import AuditLogOut
from app.services.audit_service import AuditService
from app.models.user import User
from app.api.deps import get_current_user

router = APIRouter()


@router.get("/", response_model=List[AuditLogOut])
async def list_audit_logs(
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    actor_user_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = AuditService(db)
    return await service.list_logs(
        current_user.org_id,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_user_id=actor_user_id,
    )
