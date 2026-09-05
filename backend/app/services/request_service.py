from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from typing import Optional
from app.models.ai_request import AIRequest
from app.models.ai_response import AIResponse
from app.models.ai_use_case import AIUseCase
from app.models.ai_provider import AIProvider
from app.models.ai_policy import AIPolicyVersion
from app.schemas.request import RequestCreate

class RequestService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_request(
        self, org_id: int, user_id: int, data: RequestCreate
    ) -> AIRequest:
        # Get use case
        result = await self.db.execute(
            select(AIUseCase).where(
                AIUseCase.id == data.use_case_id,
                AIUseCase.org_id == org_id
            )
        )
        use_case = result.scalar_one_or_none()
        if not use_case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Use case not found"
            )
        
        # Get provider
        result = await self.db.execute(
            select(AIProvider).where(
                AIProvider.id == data.provider_id,
                AIProvider.org_id == org_id
            )
        )
        provider = result.scalar_one_or_none()
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Provider not found"
            )
        
        # Determine risk level from use case
        risk_level = use_case.risk_level
        
        # Check policy if use case has approved policy
        requires_approval = False
        if use_case.approved_policy_version_id:
            result = await self.db.execute(
                select(AIPolicyVersion).where(
                    AIPolicyVersion.id == use_case.approved_policy_version_id
                )
            )
            policy_version = result.scalar_one_or_none()
            if policy_version and policy_version.rules_json:
                rules = policy_version.rules_json
                effect = rules.get("effect")
                if effect == "require_approval":
                    requires_approval = True
        
        # Create request
        request = AIRequest(
            org_id=org_id,
            use_case_id=data.use_case_id,
            user_id=user_id,
            provider_id=data.provider_id,
            input_text=data.input_text,
            purpose=data.purpose,
            risk_level=risk_level,
            status="pending_approval" if requires_approval else "pending"
        )
        self.db.add(request)
        await self.db.commit()
        await self.db.refresh(request)
        
        # If no approval required, simulate provider call
        if not requires_approval:
            await self.process_request(request.id, org_id)
            await self.db.refresh(request)
        
        return request
    
    async def process_request(self, request_id: int, org_id: int) -> AIResponse:
        result = await self.db.execute(
            select(AIRequest).where(
                AIRequest.id == request_id,
                AIRequest.org_id == org_id
            )
        )
        request = result.scalar_one_or_none()
        if not request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Request not found"
            )
        
        # Mock provider response
        response = AIResponse(
            request_id=request.id,
            provider_response_json={"mock": True},
            response_text=f"Mock response for: {request.input_text[:50]}...",
            confidence_score=0.95
        )
        self.db.add(response)
        
        # Update request status
        request.status = "completed"
        
        await self.db.commit()
        await self.db.refresh(response)
        
        return response
    
    async def get_request(self, request_id: int, org_id: int) -> AIRequest:
        result = await self.db.execute(
            select(AIRequest).where(
                AIRequest.id == request_id,
                AIRequest.org_id == org_id
            )
        )
        request = result.scalar_one_or_none()
        if not request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Request not found"
            )
        return request
    
    async def list_requests(self, org_id: int):
        result = await self.db.execute(
            select(AIRequest).where(AIRequest.org_id == org_id).order_by(AIRequest.created_at.desc())
        )
        return list(result.scalars().all())
