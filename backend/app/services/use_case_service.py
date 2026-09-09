from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from typing import List, Optional
from app.models.ai_use_case import AIUseCase
from app.schemas.use_case import UseCaseCreate, UseCaseUpdate

class UseCaseService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_use_case(self, org_id: int, data: UseCaseCreate) -> AIUseCase:
        use_case = AIUseCase(
            org_id=org_id,
            name=data.name,
            owner_user_id=data.owner_user_id,
            risk_level=data.risk_level,
            allowed_providers_json=data.allowed_providers_json,
            approved_policy_version_id=data.approved_policy_version_id,
            status="active"
        )
        self.db.add(use_case)
        await self.db.commit()
        await self.db.refresh(use_case)
        return use_case
    
    async def get_use_case(self, use_case_id: int, org_id: int) -> AIUseCase:
        result = await self.db.execute(
            select(AIUseCase).where(
                AIUseCase.id == use_case_id,
                AIUseCase.org_id == org_id
            )
        )
        use_case = result.scalar_one_or_none()
        if not use_case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Use case not found"
            )
        return use_case
    
    async def list_use_cases(self, org_id: int) -> List[AIUseCase]:
        result = await self.db.execute(
            select(AIUseCase).where(AIUseCase.org_id == org_id)
        )
        return list(result.scalars().all())
    
    async def update_use_case(
        self, use_case_id: int, org_id: int, data: UseCaseUpdate
    ) -> AIUseCase:
        use_case = await self.get_use_case(use_case_id, org_id)
        
        if data.name is not None:
            use_case.name = data.name
        if data.owner_user_id is not None:
            use_case.owner_user_id = data.owner_user_id
        if data.risk_level is not None:
            use_case.risk_level = data.risk_level
        if data.allowed_providers_json is not None:
            use_case.allowed_providers_json = data.allowed_providers_json
        if data.approved_policy_version_id is not None:
            use_case.approved_policy_version_id = data.approved_policy_version_id
        if data.status is not None:
            use_case.status = data.status
        
        await self.db.commit()
        await self.db.refresh(use_case)
        return use_case

