from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from pathlib import Path
import os
import re
import tempfile
import zipfile
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


@router.post("/{job_id}/cancel", response_model=TrainingJobOut)
async def cancel_training_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = TrainingService(db)
    job = await service.cancel_job(job_id, current_user.org_id)
    await AuditService(db).log(
        current_user.org_id, current_user.id, "training_job", job.id, "cancelled", None,
    )
    return job


@router.post("/{job_id}/retry", response_model=TrainingJobOut)
async def retry_training_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = TrainingService(db)
    job = await service.retry_job(job_id, current_user.org_id)
    await AuditService(db).log(
        current_user.org_id, current_user.id, "training_job", job.id, "retried", None,
    )
    return job


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


@router.get("/{job_id}/download")
async def download_model(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = TrainingService(db)
    job = await service.get_job(job_id, current_user.org_id)

    if job.status != "completed" or not job.model_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This training job has no completed model to download.",
        )

    model_path = Path(job.model_path)
    if not model_path.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Model artifact is missing on disk.",
        )

    safe_name = re.sub(r"[^A-Za-z0-9_.-]", "_", job.name) or f"job_{job.id}"

    await AuditService(db).log(
        current_user.org_id, current_user.id, "training_job", job.id, "downloaded", None,
    )

    if model_path.is_file():
        # sklearn track: already a single self-contained .joblib bundle
        # (model + feature_columns + label_classes).
        return FileResponse(
            path=str(model_path),
            filename=f"{safe_name}.joblib",
            media_type="application/octet-stream",
        )

    # Transformer track: model_path is a directory (weights + tokenizer +
    # config + meta.json). Zip it on the fly into a temp file and clean up
    # once the response has been fully sent. For larger GPU-trained models
    # this can take a few seconds - that's expected.
    tmp_fd, tmp_path_str = tempfile.mkstemp(suffix=".zip")
    os.close(tmp_fd)
    tmp_path = Path(tmp_path_str)
    with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in model_path.rglob("*"):
            if file.is_file() and "_trainer_tmp" not in file.parts:
                zf.write(file, arcname=file.relative_to(model_path))

    return FileResponse(
        path=str(tmp_path),
        filename=f"{safe_name}.zip",
        media_type="application/zip",
        background=BackgroundTask(lambda: tmp_path.unlink(missing_ok=True)),
    )
