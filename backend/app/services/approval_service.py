from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from typing import List
from app.models.ai_approval import AIApproval
from app.models.ai_request import AIRequest
from app.schemas.approval import ApprovalCreate, ApprovalDecision

class ApprovalService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_approval(self, org_id: int, data: ApprovalCreate) -> AIApproval:
        # Check request exists
        result = await self.db.execute(
            select(AIRequest).where(
                AIRequest.id == data.request_id,
                AIRequest.org_id == org_id
            )
        )
        request = result.scalar_one_or_none()
        if not request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Request not found"
            )
        
        approval = AIApproval(
            request_id=data.request_id,
            approver_user_id=data.approver_user_id
        )
        self.db.add(approval)
        
        # Update request status
        request.status = "pending_approval"
        
        await self.db.commit()
        await self.db.refresh(approval)
        return approval
    
    async def make_decision(
        self, approval_id: int, org_id: int, data: ApprovalDecision
    ) -> AIApproval:
        result = await self.db.execute(
            select(AIApproval).join(AIRequest).where(
                AIApproval.id == approval_id,
                AIRequest.org_id == org_id
            )
        )
        approval = result.scalar_one_or_none()
        if not approval:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Approval not found"
            )
        
        approval.decision = data.decision
        approval.reason = data.reason
        
        # Update request status
        result = await self.db.execute(
            select(AIRequest).where(AIRequest.id == approval.request_id)
        )
        request = result.scalar_one_or_none()
        if request:
            if data.decision == "approved":
                request.status = "approved"
            else:
                request.status = "rejected"
        
        await self.db.commit()
        await self.db.refresh(approval)

        # An approved request still needs to actually run - this used to be
        # a silent no-op (status flipped to "approved" and nothing else ever
        # happened, so approved requests never got a response). Process it
        # now that a human has signed off.
        if request and data.decision == "approved":
            from app.services.request_service import RequestService

            await RequestService(self.db).process_request(request.id, org_id)

        return approval
    
    async def list_approvals(self, org_id: int) -> List[AIApproval]:
        result = await self.db.execute(
            select(AIApproval).join(AIRequest).where(
                AIRequest.org_id == org_id
            ).order_by(AIApproval.created_at.desc())
        )
        return list(result.scalars().all())
