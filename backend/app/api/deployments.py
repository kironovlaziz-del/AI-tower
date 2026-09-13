from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.core.pagination import PaginationParams
from app.schemas.pagination import Page
from app.schemas.deployment import (
    DeploymentCreate,
    DeploymentOut,
    DeploymentUpdate,
    DeploymentPredictRequest,
    DeploymentPredictResponse,
    DeploymentChatRequest,
    DeploymentChatResponse,
)
from app.services.deployment_service import DeploymentService
from app.services import notification_service
from app.services.audit_service import AuditService
from app.models.user import User, UserRole
from app.api.deps import get_current_user, require_role

router = APIRouter()


@router.post("/", response_model=DeploymentOut)
async def create_deployment(
    data: DeploymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    service = DeploymentService(db)
    dep = await service.create_deployment(
        current_user.org_id, current_user.id, data
    )
    await AuditService(db).log(
        current_user.org_id, current_user.id, "deployment", dep.id, "created",
        {"name": dep.name, "version": dep.version, "training_job_id": dep.training_job_id},
    )
    await notification_service.notify(
        db,
        current_user.org_id,
        "deployment_created",
        f"Deployment '{dep.name}' v{dep.version} created",
        f"Training job #{dep.training_job_id} is now live as '{dep.name}' v{dep.version}.",
        {
            "deployment_id": dep.id,
            "name": dep.name,
            "version": dep.version,
            "training_job_id": dep.training_job_id,
            "traffic_weight": dep.traffic_weight,
        },
    )
    return dep


@router.get("/", response_model=Page[DeploymentOut])
async def list_deployments(
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = DeploymentService(db)
    items, total = await service.list_deployments(
        current_user.org_id, skip=pagination.skip, limit=pagination.limit
    )
    return Page(
        items=items, total=total, skip=pagination.skip, limit=pagination.limit
    )


@router.get("/{deployment_id}", response_model=DeploymentOut)
async def get_deployment(
    deployment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = DeploymentService(db)
    return await service.get_deployment(deployment_id, current_user.org_id)


@router.put("/{deployment_id}", response_model=DeploymentOut)
async def update_deployment(
    deployment_id: int,
    data: DeploymentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    service = DeploymentService(db)
    dep = await service.update_deployment(
        deployment_id, current_user.org_id, data
    )
    await AuditService(db).log(
        current_user.org_id, current_user.id, "deployment", dep.id, "updated",
        data.model_dump(exclude_unset=True),
    )
    await notification_service.notify(
        db,
        current_user.org_id,
        "deployment_updated",
        f"Deployment '{dep.name}' v{dep.version} updated",
        f"Changes: {data.model_dump(exclude_unset=True)}",
        {
            "deployment_id": dep.id,
            "name": dep.name,
            "version": dep.version,
            "changes": data.model_dump(exclude_unset=True),
            "status": dep.status,
            "traffic_weight": dep.traffic_weight,
        },
    )
    return dep


@router.delete("/{deployment_id}")
async def delete_deployment(
    deployment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    service = DeploymentService(db)
    await service.delete_deployment(deployment_id, current_user.org_id)
    await AuditService(db).log(
        current_user.org_id, current_user.id, "deployment", deployment_id,
        "archived", None,
    )
    await notification_service.notify(
        db,
        current_user.org_id,
        "deployment_archived",
        f"Deployment #{deployment_id} archived",
        "This deployment is no longer served and cannot accept traffic.",
        {"deployment_id": deployment_id},
    )
    return {"status": "archived"}


@router.post("/{deployment_id}/predict", response_model=DeploymentPredictResponse)
async def predict(
    deployment_id: int,
    data: DeploymentPredictRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = DeploymentService(db)
    result = await service.predict(
        deployment_id, current_user.org_id, data.features
    )
    return DeploymentPredictResponse(**result)


@router.post("/{deployment_id}/chat", response_model=DeploymentChatResponse)
async def chat(
    deployment_id: int,
    data: DeploymentChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Interactive inference endpoint used by the in-UI playground. Text in,
    text out - the response is shaped based on the deployment's task type.
    """
    service = DeploymentService(db)
    result = await service.chat(deployment_id, current_user.org_id, data.message)
    return DeploymentChatResponse(**result)

@router.post("/by-name/{name}/predict")
async def route_predict(
    name: str,
    data: DeploymentPredictRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Route a prediction by logical deployment name.

    If multiple active deployments share `name`, one is chosen at random
    proportional to its traffic_weight. If only one matches, it always
    receives the request.
    """
    service = DeploymentService(db)
    result = await service.route_predict(current_user.org_id, name, data.features)
    return result
