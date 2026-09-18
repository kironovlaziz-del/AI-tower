from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.pagination import PaginationParams
from app.schemas.ingestion_source import (
    IngestionSourceCreate,
    IngestionSourceUpdate,
    IngestionSourceOut,
    IngestionSourceCreated,
)
from app.schemas.pagination import Page
from app.services.ingestion_source_service import IngestionSourceService
from app.services.audit_service import AuditService
from app.models.user import User, UserRole
from app.api.deps import require_role

router = APIRouter()


@router.post("/", response_model=IngestionSourceCreated)
async def create_source(
    data: IngestionSourceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    service = IngestionSourceService(db)
    source, raw_key = await service.create_source(current_user.org_id, current_user.id, data)
    await AuditService(db).log(
        current_user.org_id, current_user.id, "ingestion_source", source.id, "created",
        {"name": source.name, "source_type": source.source_type},
    )
    return IngestionSourceCreated(
        **IngestionSourceOut.model_validate(source).model_dump(), api_key=raw_key
    )


@router.get("/", response_model=Page[IngestionSourceOut])
async def list_sources(
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    service = IngestionSourceService(db)
    items, total = await service.list_sources(
        current_user.org_id, skip=pagination.skip, limit=pagination.limit
    )
    return Page(items=items, total=total, skip=pagination.skip, limit=pagination.limit)


@router.put("/{source_id}", response_model=IngestionSourceOut)
async def update_source(
    source_id: int,
    data: IngestionSourceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    service = IngestionSourceService(db)
    source = await service.update_source(source_id, current_user.org_id, data)
    await AuditService(db).log(
        current_user.org_id, current_user.id, "ingestion_source", source.id, "updated",
        data.model_dump(exclude_unset=True),
    )
    return source


@router.delete("/{source_id}", response_model=IngestionSourceOut)
async def revoke_source(
    source_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    service = IngestionSourceService(db)
    source = await service.revoke_source(source_id, current_user.org_id)
    await AuditService(db).log(
        current_user.org_id, current_user.id, "ingestion_source", source.id, "revoked", {},
    )
    return source
