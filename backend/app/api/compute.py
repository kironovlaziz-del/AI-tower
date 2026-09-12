from fastapi import APIRouter, Depends, Query
from app.schemas.compute import ComputeStatusOut
from app.services import compute_detector
from app.services import transformer_models
from app.models.user import User
from app.api.deps import get_current_user

router = APIRouter()


@router.get("/status", response_model=ComputeStatusOut)
async def get_compute_status(
    current_user: User = Depends(get_current_user),
):
    status = compute_detector.get_status()
    return ComputeStatusOut(**status.__dict__)


@router.get("/allowed-models")
async def get_allowed_models(
    task_type: str = Query(
        "transformer_text_classification",
        description="transformer_text_classification or transformer_text_generation",
    ),
    current_user: User = Depends(get_current_user),
):
    status = compute_detector.get_status()
    return {
        "gpu_available": status.gpu_available,
        "gpu_vram_total_gb": status.gpu_vram_total_gb,
        "gpu_vram_free_gb": status.gpu_vram_free_gb,
        "models": transformer_models.allowed_models(
            status.gpu_available, status.gpu_vram_free_gb, task_type
        ),
        # Free-form HF model id is only safe when we know we have a GPU big
        # enough to survive an unexpected OOM at train time.
        "custom_model_allowed": status.gpu_available,
    }
