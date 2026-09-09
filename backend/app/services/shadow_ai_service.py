from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException, status
from typing import List, Optional
from datetime import datetime, timezone
from app.models.shadow_ai_sighting import ShadowAISighting
from app.models.ai_provider import AIProvider
from app.schemas.shadow_ai import (
    ShadowSightingCreate,
    ShadowSightingUpdate,
    ShadowSightingRegister,
)


class ShadowAIService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_sighting(
        self, org_id: int, reported_by: int, data: ShadowSightingCreate
    ) -> ShadowAISighting:
        sighting = ShadowAISighting(
            org_id=org_id,
            tool_name=data.tool_name,
            domain=data.domain,
            detected_via=data.detected_via,
            user_hint=data.user_hint,
            notes=data.notes,
            status="new",
            reported_by=reported_by,
        )
        self.db.add(sighting)
        await self.db.commit()
        await self.db.refresh(sighting)
        return sighting

    async def list_sightings(
        self, org_id: int, status_filter: Optional[str] = None
    ) -> List[ShadowAISighting]:
        query = select(ShadowAISighting).where(ShadowAISighting.org_id == org_id)
        if status_filter:
            query = query.where(ShadowAISighting.status == status_filter)
        query = query.order_by(ShadowAISighting.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def _get(self, sighting_id: int, org_id: int) -> ShadowAISighting:
        result = await self.db.execute(
            select(ShadowAISighting).where(
                ShadowAISighting.id == sighting_id,
                ShadowAISighting.org_id == org_id,
            )
        )
        sighting = result.scalar_one_or_none()
        if not sighting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shadow AI sighting not found",
            )
        return sighting

    async def update_status(
        self, sighting_id: int, org_id: int, data: ShadowSightingUpdate
    ) -> ShadowAISighting:
        sighting = await self._get(sighting_id, org_id)
        if data.status is not None:
            sighting.status = data.status
            if data.status in ("dismissed", "confirmed_shadow"):
                sighting.resolved_at = datetime.now(timezone.utc)
        if data.notes is not None:
            sighting.notes = data.notes
        await self.db.commit()
        await self.db.refresh(sighting)
        return sighting

    async def register_as_provider(
        self, sighting_id: int, org_id: int, data: ShadowSightingRegister
    ) -> ShadowAISighting:
        sighting = await self._get(sighting_id, org_id)
        if sighting.status == "registered":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This sighting has already been registered as a provider.",
            )

        provider = AIProvider(
            org_id=org_id,
            name=sighting.tool_name,
            type=data.provider_type,
            status="active",
            sla=data.provider_sla,
            risk_score=0.0,
        )
        self.db.add(provider)
        await self.db.flush()

        sighting.status = "registered"
        sighting.registered_provider_id = provider.id
        sighting.resolved_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(sighting)
        return sighting

    async def summary_counts(self, org_id: int) -> dict:
        result = await self.db.execute(
            select(ShadowAISighting.status, func.count(ShadowAISighting.id))
            .where(ShadowAISighting.org_id == org_id)
            .group_by(ShadowAISighting.status)
        )
        return {row[0]: row[1] for row in result.all()}
