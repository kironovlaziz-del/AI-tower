"""
Scheduled re-verification of stored service connections.

Registered on Celery beat (see celery_app.py's beat_schedule) to run
periodically: it re-binds every ServiceConnection with its stored
credentials and refreshes last_verified_at / last_error, so the UI can
show whether saved AD/DNS credentials still work without an admin
manually checking. Runs unattended — verify_connection never raises, it
records failures as state.
"""

import asyncio
import logging
from typing import Any, Dict

from app.core.celery_app import celery_app
from app.core.celery_database import CelerySessionLocal
from app.services.discovery_service import DiscoveryService

logger = logging.getLogger("discovery_tasks")


async def _reverify_all_async() -> Dict[str, int]:
    async with CelerySessionLocal() as db:
        service = DiscoveryService(db)
        checked, ok, failed = await service.reverify_all()
        return {"checked": checked, "ok": ok, "failed": failed}


@celery_app.task(name="discovery.reverify_connections")
def reverify_connections() -> Dict[str, Any]:
    """Celery entry point. Same async→sync bridge as the other workers
    (dedicated NullPool engine, fresh event loop per invocation)."""
    result = asyncio.run(_reverify_all_async())
    logger.info(
        "discovery.reverify_connections: checked=%(checked)s ok=%(ok)s failed=%(failed)s",
        result,
    )
    return result
