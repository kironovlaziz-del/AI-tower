from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.core.database import get_db
from app.schemas.training_job import (
    TrainingJobCreate,
    TrainingJobOut,
    PredictRequest,
    PredictResponse,
)
from app.services.training_service import TrainingService
from app.services.audit_service import AuditService
from app.models.user import User
from app.api.deps import get_current_user

router = APIRouter()


@router.post("/", response_model=TrainingJobOut)
async def create_training_job(
    data: TrainingJobCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = TrainingService(db)
    job = await service.create_job(current_user.org_id, current_user.id, data)
    await AuditService(db).log(
        current_user.org_id, current_user.id, "training_job", job.id, "created",
        {"name": job.name, "algorithm": job.algorithm, "dataset_id": job.dataset_id},
    )
    return job


@router.get("/", response_model=List[TrainingJobOut])
async def list_training_jobs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = TrainingService(db)
    return await service.list_jobs(current_user.org_id)


@router.get("/{job_id}", response_model=TrainingJobOut)
async def get_training_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = TrainingService(db)
    return await service.get_job(job_id, current_user.org_id)


@router.post("/{job_id}/predict", response_model=PredictResponse)
async def predict(
    job_id: int,
    data: PredictRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = TrainingService(db)
    prediction = await service.predict(job_id, current_user.org_id, data.features)
    return PredictResponse(prediction=prediction)
