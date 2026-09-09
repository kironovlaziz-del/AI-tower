from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Any, Dict, List, Optional
from app.models.audit_log import AIAuditLog


class AuditService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(
        self,
        org_id: int,
        actor_user_id: Optional[int],
        entity_type: str,
        entity_id: Optional[int],
        action: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AIAuditLog:
        entry = AIAuditLog(
            org_id=org_id,
            actor_user_id=actor_user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            metadata_json=metadata,
        )
        self.db.add(entry)
        await self.db.commit()
        await self.db.refresh(entry)
        return entry

    async def list_logs(
        self,
        org_id: int,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        actor_user_id: Optional[int] = None,
        limit: int = 300,
    ) -> List[AIAuditLog]:
        query = select(AIAuditLog).where(AIAuditLog.org_id == org_id)
        if entity_type:
            query = query.where(AIAuditLog.entity_type == entity_type)
        if entity_id is not None:
            query = query.where(AIAuditLog.entity_id == entity_id)
        if actor_user_id is not None:
            query = query.where(AIAuditLog.actor_user_id == actor_user_id)
        query = query.order_by(AIAuditLog.created_at.desc()).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())
