from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from typing import List
from app.models.ai_request import AIRequest
from app.models.ai_override import AIOverride
from app.schemas.override import OverrideCreate


class OverrideService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_request(self, request_id: int, org_id: int) -> AIRequest:
        result = await self.db.execute(
            select(AIRequest).where(
                AIRequest.id == request_id,
                AIRequest.org_id == org_id,
            )
        )
        request = result.scalar_one_or_none()
        if not request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Request not found",
            )
        return request

    async def create_override(
        self, org_id: int, operator_user_id: int, data: OverrideCreate
    ) -> AIOverride:
        request = await self._get_request(data.request_id, org_id)

        if data.override_type == "stop":
            if request.status not in ("pending", "pending_approval"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Only a request that is pending or pending_approval "
                        "can be stopped."
                    ),
                )
            request.status = "stopped"

        elif data.override_type == "edit":
            new_text = (data.override_payload_json or {}).get("masked_input_text")
            if not new_text:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="override_payload_json.masked_input_text is required for an edit override.",
                )
            if request.status not in ("pending", "pending_approval"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Only a request that is pending or pending_approval "
                        "can have its prompt edited."
                    ),
                )
            request.masked_input_text = new_text
            flags = list(request.firewall_flags or [])
            flags.append("manually_edited")
            request.firewall_flags = flags

        elif data.override_type == "rollback":
            if request.status not in ("completed", "approved"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Only a completed request can be rolled back.",
                )
            request.status = "rolled_back"

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unknown override_type.",
            )

        override = AIOverride(
            request_id=request.id,
            override_type=data.override_type,
            override_payload_json=data.override_payload_json,
            operator_user_id=operator_user_id,
        )
        self.db.add(override)
        await self.db.commit()
        await self.db.refresh(override)
        return override

    async def list_overrides(self, org_id: int, request_id: int) -> List[AIOverride]:
        # Ensure the request belongs to this org before exposing its overrides
        await self._get_request(request_id, org_id)
        result = await self.db.execute(
            select(AIOverride)
            .where(AIOverride.request_id == request_id)
            .order_by(AIOverride.created_at.desc())
        )
        return list(result.scalars().all())
