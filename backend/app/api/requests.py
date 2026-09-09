from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.core.database import get_db
from app.schemas.request import RequestCreate, RequestOut, ResponseOut
from app.services.request_service import RequestService
from app.services.audit_service import AuditService
from app.services import notification_service
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
    ai_request = await service.create_request(current_user.org_id, current_user.id, data)
    await AuditService(db).log(
        current_user.org_id, current_user.id, "request", ai_request.id,
        "blocked" if ai_request.status == "blocked" else "created",
        {
            "purpose": ai_request.purpose,
            "risk_level": ai_request.risk_level,
            "status": ai_request.status,
            "firewall_flags": ai_request.firewall_flags,
        },
    )
    if ai_request.status == "blocked":
        await notification_service.notify(
            db, current_user.org_id, "request_blocked",
            "Запрос заблокирован Prompt Firewall",
            f"Запрос #{ai_request.id} ({ai_request.purpose}) заблокирован по блок-листу политики.",
            {"request_id": ai_request.id},
        )
    return ai_request

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


@router.get("/{request_id}/response", response_model=Optional[ResponseOut])
async def get_request_response(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = RequestService(db)
    return await service.get_response(request_id, current_user.org_id)
