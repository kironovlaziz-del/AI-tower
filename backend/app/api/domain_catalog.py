from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.pagination import PaginationParams
from app.schemas.domain_catalog import (
    DomainCatalogCreate,
    DomainCatalogUpdate,
    DomainCatalogOut,
)
from app.schemas.pagination import Page
from app.services.domain_catalog_service import DomainCatalogService
from app.services.domain_catalog_seed import SEED_DOMAINS
from app.services.audit_service import AuditService
from app.models.user import User, UserRole
from app.api.deps import require_role, get_current_user

router = APIRouter()


@router.post("/import-known")
async def import_known_domains(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    """Bulk-add the built-in known AI domains to this org's catalog as
    'unknown' (needs review). Admin only; skips domains already present."""
    service = DomainCatalogService(db)
    result = await service.import_seed(current_user.org_id)
    await AuditService(db).log(
        current_user.org_id, current_user.id, "domain_catalog", 0, "import_known",
        result,
    )
    return result


@router.get("/seed-suggestions")
async def seed_suggestions(current_user: User = Depends(get_current_user)):
    """The built-in known-domain hints, so an admin can quickly add
    catalog entries with tool_name/category pre-filled instead of typing
    them from scratch."""
    return {"suggestions": SEED_DOMAINS}


@router.post("/", response_model=DomainCatalogOut)
async def create_entry(
    data: DomainCatalogCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    service = DomainCatalogService(db)
    entry = await service.create_entry(current_user.org_id, data)
    await AuditService(db).log(
        current_user.org_id, current_user.id, "ai_domain_catalog", entry.id, "created",
        {"domain": entry.domain, "policy_status": entry.policy_status},
    )
    return entry


@router.get("/", response_model=Page[DomainCatalogOut])
async def list_entries(
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = DomainCatalogService(db)
    items, total = await service.list_entries_page(
        current_user.org_id, skip=pagination.skip, limit=pagination.limit
    )
    return Page(items=items, total=total, skip=pagination.skip, limit=pagination.limit)


@router.put("/{entry_id}", response_model=DomainCatalogOut)
async def update_entry(
    entry_id: int,
    data: DomainCatalogUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    service = DomainCatalogService(db)
    entry = await service.update_entry(entry_id, current_user.org_id, data)
    await AuditService(db).log(
        current_user.org_id, current_user.id, "ai_domain_catalog", entry.id, "updated",
        data.model_dump(exclude_unset=True),
    )
    return entry


@router.delete("/{entry_id}")
async def delete_entry(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    service = DomainCatalogService(db)
    await service.delete_entry(entry_id, current_user.org_id)
    await AuditService(db).log(
        current_user.org_id, current_user.id, "ai_domain_catalog", entry_id, "deleted", {},
    )
    return {"status": "deleted"}
