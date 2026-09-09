from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ShadowSightingCreate(BaseModel):
    tool_name: str
    domain: Optional[str] = None
    detected_via: str = "manual"  # manual, expense_report, network_proxy, browser_extension, other
    user_hint: Optional[str] = None
    notes: Optional[str] = None


class ShadowSightingUpdate(BaseModel):
    status: Optional[str] = None  # reviewing, confirmed_shadow, dismissed
    notes: Optional[str] = None


class ShadowSightingRegister(BaseModel):
    provider_type: str = "custom"
    provider_sla: Optional[str] = None


class ShadowSightingOut(BaseModel):
    id: int
    org_id: int
    tool_name: str
    domain: Optional[str]
    detected_via: str
    user_hint: Optional[str]
    notes: Optional[str]
    status: str
    reported_by: Optional[int]
    registered_provider_id: Optional[int]
    created_at: datetime
    resolved_at: Optional[datetime]

    class Config:
        from_attributes = True
