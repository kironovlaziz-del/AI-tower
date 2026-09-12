from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


class ApprovalCreate(BaseModel):
    # Reject unknown fields so that a client sending approver_user_id gets
    # a clear 422 instead of silently having it ignored. The approver is
    # assigned server-side - see services/approval_service.py.
    model_config = ConfigDict(extra="forbid")

    request_id: int


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
