from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional, Literal

EVENT_TYPES = [
    "incident_created",
    "approval_pending",
    "shadow_ai_reported",
    "request_blocked",
    "training_completed",
    "training_failed",
]


class NotificationChannelCreate(BaseModel):
    channel_type: Literal["email", "webhook"]
    target: str
    events: List[str]
    enabled: bool = True


class NotificationChannelUpdate(BaseModel):
    target: Optional[str] = None
    events: Optional[List[str]] = None
    enabled: Optional[bool] = None


class NotificationChannelOut(BaseModel):
    id: int
    org_id: int
    channel_type: str
    target: str
    events_json: List[str]
    enabled: bool
    created_by: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True
