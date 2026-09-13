from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from app.core.database import get_db
from app.models.prediction_log import PredictionLog
from app.models.model_deployment import ModelDeployment
from app.models.user import User
from app.api.deps import get_current_user
from app.services import deployment_service
from app.core.errors import api_error
from fastapi import status


router = APIRouter()


@router.get("/{deployment_id}/monitoring")
async def monitoring_summary(
    deployment_id: int,
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Aggregated monitoring metrics for a single deployment over the last
    N days. Includes per-day prediction counts, per-class distribution,
    latency percentiles, and feedback split.
    """
    # Ensure deployment belongs to this org.
    deployment_service_instance = deployment_service.DeploymentService(db)
    dep = await deployment_service_instance.get_deployment(
        deployment_id, current_user.org_id
    )

    since = datetime.now(timezone.utc) - timedelta(days=days)

    base_filter = [
        PredictionLog.deployment_id == deployment_id,
        PredictionLog.org_id == current_user.org_id,
        PredictionLog.created_at >= since,
    ]

    # Time series: predictions per day
    bucket = func.date_trunc("day", PredictionLog.created_at).label("day")
    rows = await db.execute(
        select(bucket, func.count())
        .where(*base_filter)
        .group_by(bucket)
        .order_by(bucket)
    )
    by_day: Dict[str, int] = {}
    for i in range(days):
        d = (datetime.now(timezone.utc) - timedelta(days=days - 1 - i)).date()
        by_day[d.isoformat()] = 0
    for day, count in rows.all():
        key = day.date().isoformat()
        if key in by_day:
            by_day[key] = int(count)

    predictions_by_day = [
        {"date": k, "count": v} for k, v in sorted(by_day.items())
    ]

    # Distribution: predictions by class
    rows = await db.execute(
        select(PredictionLog.prediction, func.count())
        .where(*base_filter)
        .group_by(PredictionLog.prediction)
    )
    by_prediction = {
        (str(k) if k is not None else "unknown"): int(v) for k, v in rows.all()
    }

    # Latency: min / avg / max
    row = await db.execute(
        select(
            func.min(PredictionLog.latency_ms),
            func.avg(PredictionLog.latency_ms),
            func.max(PredictionLog.latency_ms),
            func.count(),
        ).where(*base_filter)
    )
    mn, avg, mx, total = row.one()
    latency = {
        "min": float(mn) if mn is not None else None,
        "avg": float(avg) if avg is not None else None,
        "max": float(mx) if mx is not None else None,
    }

    # Feedback split
    rows = await db.execute(
        select(PredictionLog.feedback, func.count())
        .where(*base_filter, PredictionLog.feedback.isnot(None))
        .group_by(PredictionLog.feedback)
    )
    feedback = {
        ("positive" if int(k) == 1 else "negative"): int(v)
        for k, v in rows.all()
    }

    # Recent predictions (last 20)
    rows = await db.execute(
        select(PredictionLog)
        .where(*base_filter)
        .order_by(desc(PredictionLog.created_at))
        .limit(20)
    )
    recent = [
        {
            "id": r.id,
            "prediction": r.prediction,
            "latency_ms": r.latency_ms,
            "features": r.features_json,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows.scalars().all()
    ]

    return {
        "deployment_id": deployment_id,
        "deployment_name": dep.name,
        "deployment_version": dep.version,
        "window_days": days,
        "total_predictions": int(total or 0),
        "predictions_by_day": predictions_by_day,
        "predictions_by_class": by_prediction,
        "latency_ms": latency,
        "feedback": feedback,
        "recent_predictions": recent,
    }
