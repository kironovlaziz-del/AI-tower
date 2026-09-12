"""
Celery tasks for the request pipeline.

The actual provider call can take tens of seconds. Running it inline in an
HTTP handler would block the response; instead the API hands the work off
to a worker, which returns immediately and updates the request row when
the provider responds.
"""

import asyncio
import traceback
from datetime import datetime, timezone

from app.core.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.models.ai_request import AIRequest
from app.services.request_service import RequestService


async def _process_request_async(request_id: int, org_id: int) -> None:
    async with AsyncSessionLocal() as db:
        try:
            await RequestService(db).process_request(request_id, org_id)
        except Exception:
            # Mark the request as failed so the UI does not spin forever.
            try:
                result = await db.execute(
                    AIRequest.__table__.select().where(AIRequest.id == request_id)
                )
                row = result.first()
                if row is not None:
                    await db.execute(
                        AIRequest.__table__.update()
                        .where(AIRequest.id == request_id)
                        .values(
                            status="failed",
                            error_message=traceback.format_exc(limit=3)[:2000],
                        )
                    )
                    await db.commit()
            except Exception:
                pass
            raise


@celery_app.task(name="request.process")
def process_request_task(request_id: int, org_id: int) -> None:
    """
    Celery wrapper around the async RequestService.process_request.
    Celery's prefork pool has no running event loop, so we spin up a fresh
    one per task invocation.
    """
    asyncio.run(_process_request_async(request_id, org_id))
