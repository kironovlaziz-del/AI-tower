from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.core.database import get_db
from app.schemas.request import RequestCreate, RequestOut, ResponseOut
from app.services.request_service import RequestService
from app.models.user import User
from app.api.deps import get_current_user

router = APIRouter()

@router.post("/", response_model=RequestOut)
async def create_request(
    data: RequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = RequestService(db)
    return await service.create_request(current_user.org_id, current_user.id, data)

@router.get("/", response_model=List[RequestOut])
async def list_requests(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = RequestService(db)
    return await service.list_requests(current_user.org_id)

@router.get("/{request_id}", response_model=RequestOut)
async def get_request(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = RequestService(db)
    return await service.get_request(request_id, current_user.org_id)
