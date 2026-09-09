from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.core.database import get_db
from app.schemas.dataset import DatasetOut
from app.services.dataset_service import DatasetService
from app.services.audit_service import AuditService
from app.models.user import User
from app.api.deps import get_current_user

router = APIRouter()


@router.post("/", response_model=DatasetOut)
async def upload_dataset(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    task_type: str = Form("other"),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = DatasetService(db)
    dataset = await service.upload_dataset(
        current_user.org_id, current_user.id, name, description, task_type, file
    )
    await AuditService(db).log(
        current_user.org_id, current_user.id, "dataset", dataset.id, "created",
        {"name": dataset.name, "task_type": dataset.task_type, "size_bytes": dataset.size_bytes},
    )
    return dataset


@router.get("/", response_model=List[DatasetOut])
async def list_datasets(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = DatasetService(db)
    return await service.list_datasets(current_user.org_id)


@router.get("/{dataset_id}", response_model=DatasetOut)
async def get_dataset(
    dataset_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = DatasetService(db)
    return await service.get_dataset(dataset_id, current_user.org_id)


@router.delete("/{dataset_id}")
async def delete_dataset(
    dataset_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = DatasetService(db)
    await service.delete_dataset(dataset_id, current_user.org_id)
    await AuditService(db).log(
        current_user.org_id, current_user.id, "dataset", dataset_id, "deleted", None,
    )
    return {"status": "deleted"}
