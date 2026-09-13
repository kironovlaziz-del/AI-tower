"""
Deployment Manager.

Wraps a completed TrainingJob into a stable, versioned endpoint that
callers can hit for inference. Actual prediction logic is reused from
TrainingService.predict - this service handles lifecycle (create,
version, status) and dispatches to the training service with the
underlying job's model artifact.
"""

from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from app.core.errors import api_error
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.models.model_deployment import ModelDeployment
from app.models.training_job import TrainingJob
from app.schemas.deployment import DeploymentCreate, DeploymentUpdate
from app.services.training_service import TrainingService


class DeploymentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_deployment(
        self, org_id: int, created_by: int, data: DeploymentCreate
    ) -> ModelDeployment:
        # 1. The underlying training job must exist, belong to this org,
        #    and have successfully produced an artifact.
        result = await self.db.execute(
            select(TrainingJob).where(
                TrainingJob.id == data.training_job_id,
                TrainingJob.org_id == org_id,
            )
        )
        job = result.scalar_one_or_none()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Training job not found",
            )
        if job.status != "completed" or not job.model_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Only a completed training job with a model artifact "
                    "can be deployed."
                ),
            )

        # 2. Pick the next version if not specified.
        version = data.version
        if version is None:
            latest = await self.db.scalar(
                select(func.max(ModelDeployment.version)).where(
                    ModelDeployment.org_id == org_id,
                    ModelDeployment.name == data.name,
                )
            )
            version = int(latest or 0) + 1

        # 3. Reject duplicate (org, name, version).
        existing = await self.db.execute(
            select(ModelDeployment).where(
                ModelDeployment.org_id == org_id,
                ModelDeployment.name == data.name,
                ModelDeployment.version == version,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Deployment '{data.name}' v{version} already exists "
                    "in this organization."
                ),
            )

        deployment = ModelDeployment(
            org_id=org_id,
            training_job_id=data.training_job_id,
            name=data.name,
            version=version,
            description=data.description,
            status="active",
            traffic_weight=data.traffic_weight,
            created_by=created_by,
        )
        self.db.add(deployment)
        await self.db.commit()
        await self.db.refresh(deployment)
        return deployment

    async def list_deployments(
        self, org_id: int, skip: int = 0, limit: int = 50
    ) -> tuple[List[ModelDeployment], int]:
        base = select(ModelDeployment).where(ModelDeployment.org_id == org_id)
        total = await self.db.scalar(
            select(func.count()).select_from(base.subquery())
        )
        result = await self.db.execute(
            base.order_by(ModelDeployment.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all()), int(total or 0)

    async def get_deployment(
        self, deployment_id: int, org_id: int
    ) -> ModelDeployment:
        result = await self.db.execute(
            select(ModelDeployment).where(
                ModelDeployment.id == deployment_id,
                ModelDeployment.org_id == org_id,
            )
        )
        dep = result.scalar_one_or_none()
        if not dep:
            raise api_error(
                status.HTTP_404_NOT_FOUND, "deployment.not_found"
            )
        return dep

    async def update_deployment(
        self, deployment_id: int, org_id: int, data: DeploymentUpdate
    ) -> ModelDeployment:
        dep = await self.get_deployment(deployment_id, org_id)
        if data.description is not None:
            dep.description = data.description
        if data.status is not None:
            dep.status = data.status
        if data.traffic_weight is not None:
            dep.traffic_weight = data.traffic_weight
        await self.db.commit()
        await self.db.refresh(dep)
        return dep

    async def delete_deployment(
        self, deployment_id: int, org_id: int
    ) -> None:
        dep = await self.get_deployment(deployment_id, org_id)
        # Soft delete: keep the row for audit trail by archiving it.
        dep.status = "archived"
        await self.db.commit()

    async def predict(
        self, deployment_id: int, org_id: int, features: Dict[str, Any]
    ) -> Dict[str, Any]:
        dep = await self.get_deployment(deployment_id, org_id)
        if dep.status != "active":
            raise api_error(
                status.HTTP_400_BAD_REQUEST,
                "deployment.not_active",
                status=dep.status,
            )

        # Fetch the underlying training job (still scoped to the same org).
        result = await self.db.execute(
            select(TrainingJob).where(
                TrainingJob.id == dep.training_job_id,
                TrainingJob.org_id == org_id,
            )
        )
        job = result.scalar_one_or_none()
        if not job or job.status != "completed" or not job.model_path:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Underlying model artifact is not available.",
            )

        training_service = TrainingService(self.db)
        prediction = await training_service.predict(
            job.id, org_id, features
        )
        return {
            "deployment_id": dep.id,
            "version": dep.version,
            "prediction": prediction,
        }

    async def route_predict(
        self, org_id: int, name: str, features: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Route a prediction by logical deployment name.

        All active deployments sharing `name` participate with their
        traffic_weight as a probability mass. The chosen deployment's
        own predict() then runs as usual, so the response shape is
        identical to a direct call.
        """
        import random

        result = await self.db.execute(
            select(ModelDeployment).where(
                ModelDeployment.org_id == org_id,
                ModelDeployment.name == name,
                ModelDeployment.status == "active",
            )
        )
        candidates = list(result.scalars().all())
        if not candidates:
            raise api_error(
                status.HTTP_404_NOT_FOUND,
                "deployment.name_not_found",
                name=name,
            )

        total_weight = sum(max(d.traffic_weight or 0.0, 0.0) for d in candidates)
        if total_weight <= 0:
            raise api_error(
                status.HTTP_400_BAD_REQUEST,
                "deployment.no_active_traffic",
                name=name,
            )

        # Weighted random selection. random.uniform gives us a value in
        # [0, total_weight); walking the list finds the bucket it falls in.
        pick = random.uniform(0, total_weight)
        chosen: ModelDeployment = candidates[-1]
        acc = 0.0
        for dep in candidates:
            acc += max(dep.traffic_weight or 0.0, 0.0)
            if pick <= acc:
                chosen = dep
                break

        # Dispatch to the chosen deployment using the existing predict
        # implementation.
        result = await self.predict(chosen.id, org_id, features)
        result["routed_to"] = {
            "id": chosen.id,
            "version": chosen.version,
            "traffic_weight": chosen.traffic_weight,
        }
        result["candidates"] = [
            {"id": d.id, "version": d.version, "traffic_weight": d.traffic_weight}
            for d in candidates
        ]
        return result

    async def chat(
        self, deployment_id: int, org_id: int, message: str
    ) -> Dict[str, Any]:
        """
        Chat endpoint for the in-UI playground.

        Only text-based models can be chatted with - tabular models need a
        feature vector, not a message. For classification models the
        "response" is the predicted label; for generation models it is
        the model's continuation of the input.
        """
        import time

        dep = await self.get_deployment(deployment_id, org_id)
        if dep.status != "active":
            raise api_error(
                status.HTTP_400_BAD_REQUEST,
                "deployment.not_active",
                status=dep.status,
            )

        result = await self.db.execute(
            select(TrainingJob).where(
                TrainingJob.id == dep.training_job_id,
                TrainingJob.org_id == org_id,
            )
        )
        job = result.scalar_one_or_none()
        if not job or job.status != "completed" or not job.model_path:
            raise api_error(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "deployment.model_unavailable",
            )

        if job.task_type == "transformer_text_classification":
            features = {"text": message}
        elif job.task_type == "transformer_text_generation":
            features = {"prompt": message, "max_new_tokens": 80}
        else:
            raise api_error(
                status.HTTP_400_BAD_REQUEST,
                "deployment.tabular_not_chat",
                task_type=job.task_type,
            )

        started = time.monotonic()
        training_service = TrainingService(self.db)
        prediction = await training_service.predict(job.id, org_id, features)
        elapsed_ms = int((time.monotonic() - started) * 1000)

        return {
            "deployment_id": dep.id,
            "version": dep.version,
            "model_type": job.task_type,
            "response": str(prediction),
            "latency_ms": elapsed_ms,
            "raw": prediction,
        }
