from pathlib import Path
from typing import Any, Dict, List

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.celery_app import celery_app
from app.models.dataset import Dataset
from app.models.training_job import TrainingJob
from app.schemas.training_job import TrainingJobCreate
from app.services import compute_detector, transformer_models

SUPPORTED_DATASET_FORMATS = {"csv", "tsv"}


class TrainingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_dataset(self, dataset_id: int, org_id: int) -> Dataset:
        result = await self.db.execute(
            select(Dataset).where(Dataset.id == dataset_id, Dataset.org_id == org_id)
        )
        dataset = result.scalar_one_or_none()
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found"
            )
        return dataset

    async def create_job(
        self, org_id: int, created_by: int, data: TrainingJobCreate
    ) -> TrainingJob:
        dataset = await self._get_dataset(data.dataset_id, org_id)

        if dataset.file_format not in SUPPORTED_DATASET_FORMATS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Training currently only supports tabular/CSV-shaped "
                    f"datasets (csv/tsv). This dataset is '{dataset.file_format}'."
                ),
            )

        hyperparameters = data.hyperparameters or {}

        if data.task_type == "transformer_text_classification":
            if not data.base_model:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="base_model is required for transformer_text_classification.",
                )
            if not hyperparameters.get("text_column"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="hyperparameters.text_column is required for transformer_text_classification.",
                )
            gpu_status = compute_detector.get_status()
            fit = transformer_models.check_model_fit(
                data.base_model, gpu_status.gpu_available, gpu_status.gpu_vram_free_gb
            )
            if not fit["allowed"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=fit["reason"] or f"'{data.base_model}' is not allowed on this hardware.",
                )
        else:
            is_classification = data.task_type == "tabular_classification"
            is_classifier_algo = data.algorithm in (
                "logistic_regression",
                "random_forest_classifier",
            )
            if not data.algorithm:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="algorithm is required for tabular training tasks.",
                )
            if is_classification != is_classifier_algo:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Algorithm '{data.algorithm}' does not match task_type '{data.task_type}'.",
                )

        job = TrainingJob(
            org_id=org_id,
            dataset_id=data.dataset_id,
            name=data.name,
            task_type=data.task_type,
            target_column=data.target_column,
            algorithm=data.algorithm,
            base_model=data.base_model,
            hyperparameters_json=hyperparameters,
            status="queued",
            created_by=created_by,
        )
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)

        # Hand off to the Celery worker by task name only - this process
        # never imports pandas/scikit-learn/torch itself.
        celery_app.send_task("training.train_model", args=[job.id])

        return job

    async def list_jobs(self, org_id: int) -> List[TrainingJob]:
        result = await self.db.execute(
            select(TrainingJob)
            .where(TrainingJob.org_id == org_id)
            .order_by(TrainingJob.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_job(self, job_id: int, org_id: int) -> TrainingJob:
        result = await self.db.execute(
            select(TrainingJob).where(TrainingJob.id == job_id, TrainingJob.org_id == org_id)
        )
        job = result.scalar_one_or_none()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Training job not found"
            )
        return job

    async def predict(
        self, job_id: int, org_id: int, features: Dict[str, Any]
    ) -> Any:
        job = await self.get_job(job_id, org_id)
        if job.status != "completed" or not job.model_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This training job has no completed model to predict with.",
            )
        if not Path(job.model_path).exists():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Model artifact is missing on disk.",
            )

        # Both branches below are blocking CPU/GPU work - run off the event
        # loop so it doesn't stall other requests.
        if job.task_type == "transformer_text_classification":
            return await run_in_threadpool(self._predict_transformer_sync, job.model_path, features)
        return await run_in_threadpool(self._predict_sync, job.model_path, features)

    @staticmethod
    def _predict_sync(model_path: str, features: Dict[str, Any]) -> Any:
        import joblib
        import pandas as pd

        bundle = joblib.load(model_path)
        model = bundle["model"]
        feature_columns = bundle["feature_columns"]
        label_classes = bundle.get("label_classes")

        row = {col: features.get(col, 0) for col in feature_columns}
        df = pd.DataFrame([row], columns=feature_columns)

        prediction = model.predict(df)[0]

        if label_classes is not None:
            try:
                prediction = label_classes[int(prediction)]
            except (IndexError, ValueError, TypeError):
                pass

        if hasattr(prediction, "item"):
            prediction = prediction.item()

        return prediction

    @staticmethod
    def _predict_transformer_sync(model_dir: str, features: Dict[str, Any]) -> Any:
        import json

        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        text = features.get("text", "")
        meta_path = Path(model_dir) / "meta.json"
        label_classes = None
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
            label_classes = meta.get("label_classes")

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        tokenizer = AutoTokenizer.from_pretrained(model_dir)
        model = AutoModelForSequenceClassification.from_pretrained(model_dir).to(device)
        model.eval()

        inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=256).to(device)
        with torch.no_grad():
            logits = model(**inputs).logits
        predicted_id = int(torch.argmax(logits, dim=-1).item())

        if label_classes is not None:
            try:
                return label_classes[predicted_id]
            except IndexError:
                return predicted_id
        return predicted_id
