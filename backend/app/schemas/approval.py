from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ApprovalCreate(BaseModel):
    request_id: int
    approver_user_id: int

class ApprovalDecision(BaseModel):
    decision: str  # approved or rejected
    reason: Optional[str] = None

class ApprovalOut(BaseModel):
    id: int
    request_id: int
    approver_user_id: Optional[int]
    decision: Optional[str]
    reason: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

