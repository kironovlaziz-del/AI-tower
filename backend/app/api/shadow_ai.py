from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.core.database import get_db
from app.schemas.shadow_ai import (
    ShadowSightingCreate,
    ShadowSightingUpdate,
    ShadowSightingRegister,
    ShadowSightingOut,
)
from app.services.shadow_ai_service import ShadowAIService
from app.services.audit_service import AuditService
from app.services import notification_service
from app.models.user import User
from app.api.deps import get_current_user, require_role
from app.models.user import UserRole

router = APIRouter()


@router.post("/", response_model=ShadowSightingOut)
async def create_sighting(
    data: ShadowSightingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ShadowAIService(db)
    sighting = await service.create_sighting(current_user.org_id, current_user.id, data)
    await AuditService(db).log(
        current_user.org_id, current_user.id, "shadow_ai_sighting", sighting.id, "created",
        {"tool_name": sighting.tool_name, "detected_via": sighting.detected_via},
    )
    await notification_service.notify(
        db, current_user.org_id, "shadow_ai_reported",
        f"Замечено несанкционированное использование AI: {sighting.tool_name}",
        f"Источник: {sighting.detected_via}. Требует разбора в Shadow AI Monitor.",
        {"sighting_id": sighting.id},
    )
    return sighting


@router.get("/", response_model=List[ShadowSightingOut])
async def list_sightings(
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ShadowAIService(db)
    return await service.list_sightings(current_user.org_id, status_filter)


@router.get("/summary")
async def summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ShadowAIService(db)
    return await service.summary_counts(current_user.org_id)


@router.put("/{sighting_id}", response_model=ShadowSightingOut)
async def update_sighting(
    sighting_id: int,
    data: ShadowSightingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ShadowAIService(db)
    sighting = await service.update_status(sighting_id, current_user.org_id, data)
    await AuditService(db).log(
        current_user.org_id, current_user.id, "shadow_ai_sighting", sighting.id,
        data.status or "updated",
        {"notes": data.notes},
    )
    return sighting


@router.post("/{sighting_id}/register", response_model=ShadowSightingOut)
async def register_sighting(
    sighting_id: int,
    data: ShadowSightingRegister,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    service = ShadowAIService(db)
    sighting = await service.register_as_provider(sighting_id, current_user.org_id, data)
    await AuditService(db).log(
        current_user.org_id, current_user.id, "shadow_ai_sighting", sighting.id, "registered",
        {"registered_provider_id": sighting.registered_provider_id},
    )
    return sighting
