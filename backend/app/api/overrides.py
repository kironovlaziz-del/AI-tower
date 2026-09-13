from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.core.database import get_db
from app.core.pagination import PaginationParams
from app.schemas.override import OverrideCreate, OverrideOut
from app.schemas.pagination import Page
from app.services.override_service import OverrideService
from app.services.audit_service import AuditService
from app.models.user import User
from app.api.deps import get_current_user

router = APIRouter()


@router.post("/", response_model=OverrideOut)
async def create_override(
    data: OverrideCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = OverrideService(db)
    override = await service.create_override(current_user.org_id, current_user.id, data)
    await AuditService(db).log(
        current_user.org_id, current_user.id, "override", override.id,
        override.override_type,
        {"request_id": override.request_id, "payload": override.override_payload_json},
    )
    return override


@router.get("/", response_model=Page[OverrideOut])
async def list_overrides(
    request_id: int,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = OverrideService(db)
    items, total = await service.list_overrides(
        current_user.org_id,
        request_id,
        skip=pagination.skip,
        limit=pagination.limit,
    )
    return Page(items=items, total=total, skip=pagination.skip, limit=pagination.limit)
