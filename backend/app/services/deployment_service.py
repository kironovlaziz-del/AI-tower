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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deployment not found",
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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Deployment is not active (current status: {dep.status}).",
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
