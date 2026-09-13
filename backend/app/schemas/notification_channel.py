from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import List, Optional, Literal

EVENT_TYPES = [
    "incident_created",
    "approval_pending",
    "shadow_ai_reported",
    "request_blocked",
    "training_completed",
    "training_failed",
    "deployment_created",
    "deployment_updated",
    "deployment_archived",
]


class NotificationChannelCreate(BaseModel):
    channel_type: Literal["email", "webhook"]
    target: str
    events: List[str]
    enabled: bool = True

    @field_validator("target")
    @classmethod
    def _validate_target(cls, v: str, info):
        channel_type = info.data.get("channel_type")
        v = v.strip()
        if not v:
            raise ValueError("target must not be empty")
        if channel_type == "email":
            # Basic structural check - enough to reject obvious typos.
            if "@" not in v or v.startswith("@") or v.endswith("@"):
                raise ValueError("invalid email address")
            # Normalize case so "Ops@Example.com" and "ops@example.com"
            # cannot coexist as two channels.
            v = v.lower()
        elif channel_type == "webhook":
            if not (v.startswith("http://") or v.startswith("https://")):
                raise ValueError("webhook URL must start with http:// or https://")
            # Strip trailing slash so /hook and /hook/ are the same target.
            if v.endswith("/") and v.count("/") > 2:
                v = v.rstrip("/")
        return v


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
