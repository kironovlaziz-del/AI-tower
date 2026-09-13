import os
import re
import shutil
import uuid
from pathlib import Path
from typing import List

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.dataset import Dataset

# Keep this in sync with what the UI + docs claim is supported. Anything
# else is rejected outright rather than silently stored as "other".
ALLOWED_EXTENSIONS = {".csv", ".json", ".jsonl", ".txt", ".tsv"}
MAX_UPLOAD_BYTES = 200 * 1024 * 1024  # 200 MB - generous for a CPU-only box


def _safe_filename(filename: str) -> str:
    name = os.path.basename(filename or "dataset")
    name = re.sub(r"[^A-Za-z0-9_.-]", "_", name)
    return name or "dataset"


class DatasetService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _org_dir(self, org_id: int) -> Path:
        path = Path(settings.DATASETS_DIR) / str(org_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    async def upload_dataset(
        self,
        org_id: int,
        uploaded_by: int,
        name: str,
        description: str | None,
        task_type: str,
        file: UploadFile,
    ) -> Dataset:
        safe_name = _safe_filename(file.filename or "dataset")
        ext = Path(safe_name).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
            )

        dest_dir = self._org_dir(org_id)
        stored_name = f"{uuid.uuid4().hex}_{safe_name}"
        dest_path = dest_dir / stored_name

        size_bytes = 0
        try:
            with open(dest_path, "wb") as out_file:
                while True:
                    chunk = await file.read(1024 * 1024)
                    if not chunk:
                        break
                    size_bytes += len(chunk)
                    if size_bytes > MAX_UPLOAD_BYTES:
                        out_file.close()
                        dest_path.unlink(missing_ok=True)
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"File exceeds the {MAX_UPLOAD_BYTES // (1024*1024)} MB limit.",
                        )
                    out_file.write(chunk)
        except HTTPException:
            raise
        except Exception:
            dest_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to store the uploaded file.",
            )

        dataset = Dataset(
            org_id=org_id,
            name=name,
            description=description,
            task_type=task_type,
            file_format=ext.lstrip("."),
            file_path=str(dest_path),
            size_bytes=size_bytes,
            uploaded_by=uploaded_by,
        )
        self.db.add(dataset)
        await self.db.commit()
        await self.db.refresh(dataset)
        return dataset

    async def list_datasets(
        self, org_id: int, skip: int = 0, limit: int = 50
    ) -> "tuple[List[Dataset], int]":
        from sqlalchemy import func

        base = select(Dataset).where(Dataset.org_id == org_id)
        total = await self.db.scalar(
            select(func.count()).select_from(base.subquery())
        )
        result = await self.db.execute(
            base.order_by(Dataset.created_at.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().all()), int(total or 0)

    async def get_dataset(self, dataset_id: int, org_id: int) -> Dataset:
        result = await self.db.execute(
            select(Dataset).where(Dataset.id == dataset_id, Dataset.org_id == org_id)
        )
        dataset = result.scalar_one_or_none()
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found"
            )
        return dataset

    async def delete_dataset(self, dataset_id: int, org_id: int) -> None:
        dataset = await self.get_dataset(dataset_id, org_id)
        try:
            Path(dataset.file_path).unlink(missing_ok=True)
        except OSError:
            pass
        await self.db.delete(dataset)
        await self.db.commit()
