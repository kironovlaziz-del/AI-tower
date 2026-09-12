from functools import lru_cache
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
TRANSFORMER_TASK_TYPES = {"transformer_text_classification", "transformer_text_generation"}



# ---------------------------------------------------------------------------
# Model cache
#
# Loading a Hugging Face model from disk takes seconds per call. Without a
# cache, every /predict request reloads the same weights from the same
# directory. The cache holds a small number of recently used artifacts; the
# (path -> object) mapping is invalidated naturally when a job is retrained
# because each retrain writes to the same job_<id> directory but the mtime
# changes - callers should pass mtime as part of the key if they need
# strict invalidation. Here we key on path only and accept stale reads
# within a worker's lifetime for simplicity.
# ---------------------------------------------------------------------------


@lru_cache(maxsize=8)
def _load_sklearn_bundle(model_path: str):
    import joblib

    return joblib.load(model_path)


@lru_cache(maxsize=4)
def _load_transformer(model_dir: str):
    """Returns (model, tokenizer) for a sequence-classification model."""
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForSequenceClassification.from_pretrained(model_dir).to(device)
    model.eval()
    return model, tokenizer, device


@lru_cache(maxsize=4)
def _load_generator(model_dir: str):
    """Returns (model, tokenizer) for a causal LM."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(model_dir).to(device)
    model.eval()
    return model, tokenizer, device



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
        target_column = data.target_column

        if data.task_type in TRANSFORMER_TASK_TYPES:
            if not data.base_model:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"base_model is required for {data.task_type}.",
                )
            text_column = hyperparameters.get("text_column")
            if not text_column:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"hyperparameters.text_column is required for {data.task_type}.",
                )

            if data.task_type == "transformer_text_classification" and not target_column:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="target_column (the label column) is required for transformer_text_classification.",
                )
            if data.task_type == "transformer_text_generation":
                # Generation is self-supervised on the text itself - there's
                # no separate label column, so target_column is just set to
                # the text column for bookkeeping/display purposes.
                target_column = text_column

            gpu_status = compute_detector.get_status()
            fit = transformer_models.check_model_fit(
                data.base_model, data.task_type, gpu_status.gpu_available, gpu_status.gpu_vram_free_gb
            )
            if not fit["allowed"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=fit["reason"] or f"'{data.base_model}' is not allowed on this hardware.",
                )
        else:
            if not target_column:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="target_column is required for tabular training tasks.",
                )
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
            target_column=target_column,
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
        result = celery_app.send_task("training.train_model", args=[job.id])
        job.celery_task_id = result.id
        await self.db.commit()
        await self.db.refresh(job)

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

    async def cancel_job(self, job_id: int, org_id: int) -> TrainingJob:
        from datetime import datetime, timezone

        job = await self.get_job(job_id, org_id)
        if job.status not in ("queued", "running"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel a job in status '{job.status}'.",
            )

        if job.celery_task_id:
            # terminate=True sends SIGKILL to the worker process actually
            # running this task, if it has started. If it's still queued,
            # this just marks it revoked so the worker skips it when it
            # would otherwise pick it up.
            celery_app.control.revoke(job.celery_task_id, terminate=True, signal="SIGKILL")

        # Set the final status here rather than waiting for the worker to
        # do it: a terminated process never reaches its own status-update
        # code, so the job would otherwise be stuck at "running" forever.
        job.status = "cancelled"
        job.finished_at = datetime.now(timezone.utc)
        job.error_message = "Остановлено пользователем."
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def retry_job(self, job_id: int, org_id: int) -> TrainingJob:
        job = await self.get_job(job_id, org_id)
        if job.status not in ("failed", "cancelled"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot retry a job in status '{job.status}'.",
            )

        job.status = "queued"
        job.error_message = None
        job.metrics_json = None
        job.model_path = None
        job.feature_columns_json = None
        job.started_at = None
        job.finished_at = None
        # Clear the previous task id before queueing a new one. Otherwise
        # a cancel hitting between commit and send_task would revoke the
        # already-finished task instead of the new one.
        job.celery_task_id = None
        # Drop any cached model for this path - the new run will overwrite
        # the artifact and stale weights must not be served.
        _load_sklearn_bundle.cache_clear()
        _load_transformer.cache_clear()
        _load_generator.cache_clear()
        await self.db.commit()

        result = celery_app.send_task("training.train_model", args=[job.id])
        job.celery_task_id = result.id
        await self.db.commit()
        await self.db.refresh(job)
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

        # All branches below are blocking CPU/GPU work - run off the event
        # loop so it doesn't stall other requests.
        if job.task_type == "transformer_text_classification":
            return await run_in_threadpool(self._predict_transformer_sync, job.model_path, features)
        if job.task_type == "transformer_text_generation":
            return await run_in_threadpool(self._predict_generation_sync, job.model_path, features)
        return await run_in_threadpool(self._predict_sync, job.model_path, features)

    @staticmethod
    def _predict_sync(model_path: str, features: Dict[str, Any]) -> Any:
        import pandas as pd

        bundle = _load_sklearn_bundle(model_path)
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

        text = features.get("text", "")
        meta_path = Path(model_dir) / "meta.json"
        label_classes = None
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
            label_classes = meta.get("label_classes")

        model, tokenizer, device = _load_transformer(model_dir)

        inputs = tokenizer(
            text, return_tensors="pt", truncation=True, padding=True, max_length=256
        ).to(device)
        with torch.no_grad():
            logits = model(**inputs).logits
        predicted_id = int(torch.argmax(logits, dim=-1).item())

        if label_classes is not None:
            try:
                return label_classes[predicted_id]
            except IndexError:
                return predicted_id
        return predicted_id

    @staticmethod
    def _predict_generation_sync(model_dir: str, features: Dict[str, Any]) -> Any:
        import torch

        prompt = features.get("prompt", "")
        max_new_tokens = int(features.get("max_new_tokens", 50))

        model, tokenizer, device = _load_generator(model_dir)

        inputs = tokenizer(prompt, return_tensors="pt").to(device)
        with torch.no_grad():
            output_ids = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=True,
                top_p=0.9,
                temperature=0.8,
                pad_token_id=tokenizer.eos_token_id,
            )
        return tokenizer.decode(output_ids[0], skip_special_tokens=True)
