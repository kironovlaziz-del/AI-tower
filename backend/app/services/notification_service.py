"""
Notification Service.

Two entry points into the same send logic:
  - notify()      - async, for use from FastAPI request handlers/services.
  - notify_sync() - sync, for use from the Celery worker (training_tasks.py),
                    which has no event loop to await into.

Email is optional: if settings.SMTP_HOST is empty, email channels are
skipped with a log line rather than failing loudly - most self-hosted
installs won't have SMTP configured on day one, and that shouldn't block
webhook notifications or the rest of the platform.
"""

import logging
import smtplib
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.notification_channel import NotificationChannel
from app.schemas.notification_channel import NotificationChannelCreate, NotificationChannelUpdate

logger = logging.getLogger("notifications")


def _send_email(target: str, subject: str, message: str) -> None:
    if not settings.SMTP_HOST:
        logger.info("SMTP not configured - skipping email notification to %s", target)
        return
    msg = MIMEText(message)
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM
    msg["To"] = target
    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            if settings.SMTP_USE_TLS:
                server.starttls()
            if settings.SMTP_USER:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM, [target], msg.as_string())
    except Exception:
        logger.exception("Failed to send email notification to %s", target)


def _send_webhook(target: str, subject: str, message: str, metadata: Optional[Dict[str, Any]]) -> None:
    try:
        with httpx.Client(timeout=10.0) as client:
            client.post(target, json={"subject": subject, "message": message, "metadata": metadata or {}})
    except httpx.HTTPError:
        logger.exception("Failed to send webhook notification to %s", target)


def _dispatch(channel: NotificationChannel, subject: str, message: str, metadata: Optional[Dict[str, Any]]) -> None:
    if not channel.enabled:
        return
    if channel.channel_type == "email":
        _send_email(channel.target, subject, message)
    elif channel.channel_type == "webhook":
        _send_webhook(channel.target, subject, message, metadata)


async def notify(
    db: AsyncSession,
    org_id: int,
    event_type: str,
    subject: str,
    message: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    result = await db.execute(
        select(NotificationChannel).where(
            NotificationChannel.org_id == org_id,
            NotificationChannel.enabled == True,  # noqa: E712
        )
    )
    for channel in result.scalars().all():
        if event_type in (channel.events_json or []):
            _dispatch(channel, subject, message, metadata)


def notify_sync(
    db: Session,
    org_id: int,
    event_type: str,
    subject: str,
    message: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    channels = (
        db.query(NotificationChannel)
        .filter(NotificationChannel.org_id == org_id, NotificationChannel.enabled == True)  # noqa: E712
        .all()
    )
    for channel in channels:
        if event_type in (channel.events_json or []):
            _dispatch(channel, subject, message, metadata)


class NotificationChannelService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_channel(
        self, org_id: int, created_by: int, data: NotificationChannelCreate
    ) -> NotificationChannel:
        channel = NotificationChannel(
            org_id=org_id,
            channel_type=data.channel_type,
            target=data.target,
            events_json=data.events,
            enabled=data.enabled,
            created_by=created_by,
        )
        self.db.add(channel)
        await self.db.commit()
        await self.db.refresh(channel)
        return channel

    async def list_channels(self, org_id: int) -> List[NotificationChannel]:
        result = await self.db.execute(
            select(NotificationChannel).where(NotificationChannel.org_id == org_id)
        )
        return list(result.scalars().all())

    async def get_channel(self, channel_id: int, org_id: int) -> NotificationChannel:
        from fastapi import HTTPException, status

        result = await self.db.execute(
            select(NotificationChannel).where(
                NotificationChannel.id == channel_id, NotificationChannel.org_id == org_id
            )
        )
        channel = result.scalar_one_or_none()
        if not channel:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification channel not found")
        return channel

    async def update_channel(
        self, channel_id: int, org_id: int, data: NotificationChannelUpdate
    ) -> NotificationChannel:
        channel = await self.get_channel(channel_id, org_id)
        if data.target is not None:
            channel.target = data.target
        if data.events is not None:
            channel.events_json = data.events
        if data.enabled is not None:
            channel.enabled = data.enabled
        await self.db.commit()
        await self.db.refresh(channel)
        return channel

    async def delete_channel(self, channel_id: int, org_id: int) -> None:
        channel = await self.get_channel(channel_id, org_id)
        await self.db.delete(channel)
        await self.db.commit()

    async def send_test(self, channel_id: int, org_id: int) -> None:
        channel = await self.get_channel(channel_id, org_id)
        _dispatch(
            channel,
            "AI Control Tower - тестовое уведомление",
            "Если вы это видите, канал уведомлений настроен верно.",
            {"test": True},
        )
