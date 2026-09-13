"""
Server-Sent Events support.

Training workers publish progress into a Redis pub/sub channel keyed by
the job id. The `/training-jobs/{id}/stream` endpoint subscribes to the
same channel and forwards every message to the browser as an SSE frame.

Why Redis pub/sub rather than an in-process queue:
- The API process and the Celery worker run in separate processes; the
  worker cannot push into an asyncio.Queue held by the API.
- When the API is later run with multiple uvicorn workers, every worker
  can subscribe to the same channel and serve any client.

Payload format on the channel is JSON:
    {"pct": 42.5, "stage": "Training step 10/24", "status": "running"}
"""

import json
from typing import Any, AsyncIterator, Dict, Optional

from redis.asyncio import Redis

from app.core.config import settings


def _channel_name(job_id: int) -> str:
    return f"training:progress:{job_id}"


def _make_client() -> Redis:
    return Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD or None,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )


async def publish_progress(
    job_id: int,
    pct: Optional[float],
    stage: Optional[str],
    status: Optional[str] = None,
) -> None:
    """
    Fire-and-forget publication. Errors are swallowed - a broken pub/sub
    channel must never fail the underlying training run.
    """
    payload: Dict[str, Any] = {"pct": pct, "stage": stage}
    if status is not None:
        payload["status"] = status
    try:
        client = _make_client()
        try:
            await client.publish(_channel_name(job_id), json.dumps(payload))
        finally:
            await client.close()
    except Exception:  # noqa: BLE001
        pass


async def subscribe_progress(job_id: int) -> AsyncIterator[Dict[str, Any]]:
    """
    Async generator that yields decoded progress payloads for the given
    job. Caller is responsible for breaking out of the loop (for example
    on client disconnect or when the status becomes terminal).
    """
    client = _make_client()
    pubsub = client.pubsub()
    await pubsub.subscribe(_channel_name(job_id))
    try:
        async for message in pubsub.listen():
            if message is None:
                continue
            if message.get("type") != "message":
                continue
            try:
                data = json.loads(message["data"])
            except (TypeError, json.JSONDecodeError):
                continue
            yield data
    finally:
        try:
            await pubsub.unsubscribe(_channel_name(job_id))
        except Exception:  # noqa: BLE001
            pass
        await pubsub.close()
        await client.close()


def publish_progress_sync(
    job_id: int,
    pct: Optional[float],
    stage: Optional[str],
    status: Optional[str] = None,
) -> None:
    """
    Sync variant used by the Celery worker (which runs in a prefork pool
    without a running event loop).
    """
    from redis import Redis as SyncRedis

    payload: Dict[str, Any] = {"pct": pct, "stage": stage}
    if status is not None:
        payload["status"] = status
    try:
        client = SyncRedis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD or None,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        try:
            client.publish(_channel_name(job_id), json.dumps(payload))
        finally:
            client.close()
    except Exception:  # noqa: BLE001
        pass
