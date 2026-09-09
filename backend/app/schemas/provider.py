from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ProviderBase(BaseModel):
    name: str
    type: str  # openai, anthropic, azure_openai, custom, ...
    status: str = "active"
    sla: Optional[str] = None
    risk_score: float = 0.0
    base_url: Optional[str] = None
    default_model: Optional[str] = None


class ProviderCreate(ProviderBase):
    api_key: Optional[str] = None  # write-only, never returned


class ProviderUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    sla: Optional[str] = None
    risk_score: Optional[float] = None
    base_url: Optional[str] = None
    default_model: Optional[str] = None
    api_key: Optional[str] = None  # write-only; omit to leave unchanged


class ProviderOut(BaseModel):
    id: int
    org_id: int
    name: str
    type: str
    status: str
    sla: Optional[str] = None
    risk_score: float
    base_url: Optional[str] = None
    default_model: Optional[str] = None
    has_credentials: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
