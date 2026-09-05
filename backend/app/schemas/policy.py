from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any

class PolicyBase(BaseModel):
    name: str
    description: Optional[str] = None

class PolicyCreate(PolicyBase):
    pass

class PolicyOut(PolicyBase):
    id: int
    org_id: int
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class PolicyVersionCreate(BaseModel):
    rules_json: Dict[str, Any]

class PolicyVersionOut(BaseModel):
    id: int
    policy_id: int
    version: int
    rules_json: Dict[str, Any]
    created_by: Optional[int]
    created_at: datetime
    approved_by: Optional[int]
    approved_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class PolicyApprove(BaseModel):
    approved: bool = True
