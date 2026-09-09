from celery import Celery
from app.core.config import settings

redis_url = f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/0"

celery_app = Celery(
    "ai_control_tower",
    broker=redis_url,
    backend=redis_url.replace("/0", "/1"),
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)

from app.workers import training_tasks  # noqa: E402,F401
