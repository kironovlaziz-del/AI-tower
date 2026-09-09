from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException, status
from typing import Optional, List
from app.models.ai_policy import AIPolicy, AIPolicyVersion
from app.schemas.policy import PolicyCreate, PolicyVersionCreate

class PolicyService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_policy(self, org_id: int, policy_data: PolicyCreate, user_id: int) -> AIPolicy:
        policy = AIPolicy(
            org_id=org_id,
            name=policy_data.name,
            description=policy_data.description,
            status="draft"
        )
        self.db.add(policy)
        await self.db.commit()
        await self.db.refresh(policy)
        
        # Create first version
        version = AIPolicyVersion(
            policy_id=policy.id,
            version=1,
            rules_json={},
            created_by=user_id
        )
        self.db.add(version)
        await self.db.commit()
        await self.db.refresh(version)
        
        return policy
    
    async def get_policy(self, policy_id: int, org_id: int) -> AIPolicy:
        result = await self.db.execute(
            select(AIPolicy).where(
                AIPolicy.id == policy_id,
                AIPolicy.org_id == org_id
            )
        )
        policy = result.scalar_one_or_none()
        if not policy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Policy not found"
            )
        return policy
    
    async def list_policies(self, org_id: int) -> List[AIPolicy]:
        result = await self.db.execute(
            select(AIPolicy).where(AIPolicy.org_id == org_id)
        )
        return list(result.scalars().all())
    
    async def create_policy_version(
        self,
        policy_id: int,
        org_id: int,
        version_data: PolicyVersionCreate,
        user_id: int
    ) -> AIPolicyVersion:
        # Check policy exists
        policy = await self.get_policy(policy_id, org_id)
        
        # Get latest version
        result = await self.db.execute(
            select(func.max(AIPolicyVersion.version)).where(
                AIPolicyVersion.policy_id == policy_id
            )
        )
        latest_version = result.scalar() or 0
        
        version = AIPolicyVersion(
            policy_id=policy_id,
            version=latest_version + 1,
            rules_json=version_data.rules_json,
            created_by=user_id
        )
        self.db.add(version)
        await self.db.commit()
        await self.db.refresh(version)
        
        return version
    
    async def approve_policy_version(
        self,
        policy_id: int,
        version_id: int,
        org_id: int,
        user_id: int
    ) -> AIPolicyVersion:
        # Check policy exists
        policy = await self.get_policy(policy_id, org_id)
        
        # Get version
        result = await self.db.execute(
            select(AIPolicyVersion).where(
                AIPolicyVersion.id == version_id,
                AIPolicyVersion.policy_id == policy_id
            )
        )
        version = result.scalar_one_or_none()
        if not version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Policy version not found"
            )
        
        version.approved_by = user_id
        version.approved_at = func.now()
        
        # Update policy status to active
        policy.status = "active"
        
        await self.db.commit()
        await self.db.refresh(version)
        
        return version
    
    async def get_policy_versions(self, policy_id: int, org_id: int) -> List[AIPolicyVersion]:
        policy = await self.get_policy(policy_id, org_id)
        
        result = await self.db.execute(
            select(AIPolicyVersion).where(
                AIPolicyVersion.policy_id == policy_id
            ).order_by(AIPolicyVersion.version.desc())
        )
        return list(result.scalars().all())
    
    async def get_active_version(self, policy_id: int, org_id: int) -> Optional[AIPolicyVersion]:
        policy = await self.get_policy(policy_id, org_id)
        
        result = await self.db.execute(
            select(AIPolicyVersion).where(
                AIPolicyVersion.policy_id == policy_id,
                AIPolicyVersion.approved_by.isnot(None)
            ).order_by(AIPolicyVersion.version.desc()).limit(1)
        )
        return result.scalar_one_or_none()

