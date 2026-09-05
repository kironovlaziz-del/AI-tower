from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.core.database import get_db
from app.schemas.incident import IncidentCreate, IncidentUpdate, IncidentOut
from app.services.incident_service import IncidentService
from app.models.user import User
from app.api.deps import get_current_user

router = APIRouter()

@router.post("/", response_model=IncidentOut)
async def create_incident(
    data: IncidentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = IncidentService(db)
    return await service.create_incident(current_user.org_id, data)

@router.get("/", response_model=List[IncidentOut])
async def list_incidents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = IncidentService(db)
    return await service.list_incidents(current_user.org_id)

@router.get("/{incident_id}", response_model=IncidentOut)
async def get_incident(
    incident_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = IncidentService(db)
    return await service.get_incident(incident_id, current_user.org_id)

@router.put("/{incident_id}", response_model=IncidentOut)
async def update_incident(
    incident_id: int,
    data: IncidentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = IncidentService(db)
    return await service.update_incident(incident_id, current_user.org_id, data)
