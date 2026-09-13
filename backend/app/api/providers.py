from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.core.database import get_db
from app.core.pagination import PaginationParams
from app.schemas.provider import ProviderCreate, ProviderOut, ProviderUpdate
from app.schemas.pagination import Page
from app.services.provider_service import ProviderService
from app.services.audit_service import AuditService
from app.models.user import User
from app.api.deps import get_current_user, require_role
from app.models.user import UserRole

router = APIRouter()


@router.post("/", response_model=ProviderOut)
async def create_provider(
    data: ProviderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin))
):
    service = ProviderService(db)
    provider = await service.create_provider(current_user.org_id, data)
    await AuditService(db).log(
        current_user.org_id, current_user.id, "provider", provider.id, "created",
        {"name": provider.name, "type": provider.type},
    )
    return provider


@router.get("/", response_model=Page[ProviderOut])
async def list_providers(
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ProviderService(db)
    items, total = await service.list_providers(
        current_user.org_id, skip=pagination.skip, limit=pagination.limit
    )
    return Page(items=items, total=total, skip=pagination.skip, limit=pagination.limit)


@router.get("/{provider_id}", response_model=ProviderOut)
async def get_provider(
    provider_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = ProviderService(db)
    return await service.get_provider(provider_id, current_user.org_id)


@router.put("/{provider_id}", response_model=ProviderOut)
async def update_provider(
    provider_id: int,
    data: ProviderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin))
):
    service = ProviderService(db)
    provider = await service.update_provider(provider_id, current_user.org_id, data)
    await AuditService(db).log(
        current_user.org_id, current_user.id, "provider", provider.id, "updated",
        data.model_dump(exclude_unset=True),
    )
    return provider
