from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.dashboard import DashboardStats
from app.services.dashboard_service import build_stats
from app.models.user import User
from app.api.deps import get_current_user

router = APIRouter()


@router.get("/stats", response_model=DashboardStats)
async def get_stats(
    days: int = Query(7, ge=1, le=90, description="Rolling window in days"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = await build_stats(db, current_user.org_id, window_days=days)
    return DashboardStats(**data)
