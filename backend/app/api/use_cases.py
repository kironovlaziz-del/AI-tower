from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.core.database import get_db
from app.schemas.use_case import UseCaseCreate, UseCaseOut, UseCaseUpdate
from app.services.use_case_service import UseCaseService
from app.models.user import User
from app.api.deps import get_current_user

router = APIRouter()

@router.post("/", response_model=UseCaseOut)
async def create_use_case(
    data: UseCaseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = UseCaseService(db)
    return await service.create_use_case(current_user.org_id, data)

@router.get("/", response_model=List[UseCaseOut])
async def list_use_cases(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = UseCaseService(db)
    return await service.list_use_cases(current_user.org_id)

@router.get("/{use_case_id}", response_model=UseCaseOut)
async def get_use_case(
    use_case_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = UseCaseService(db)
    return await service.get_use_case(use_case_id, current_user.org_id)

@router.put("/{use_case_id}", response_model=UseCaseOut)
async def update_use_case(
    use_case_id: int,
    data: UseCaseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = UseCaseService(db)
    return await service.update_use_case(use_case_id, current_user.org_id, data)
