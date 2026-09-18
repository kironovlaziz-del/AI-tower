from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Literal


class IngestionSourceCreate(BaseModel):
    name: str
    source_type: Literal["gateway", "endpoint", "browser_extension"]


class IngestionSourceUpdate(BaseModel):
    name: Optional[str] = None
    enabled: Optional[bool] = None


class IngestionSourceOut(BaseModel):
    id: int
    org_id: int
    name: str
    source_type: str
    enabled: bool
    last_seen_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class IngestionSourceCreated(IngestionSourceOut):
    """Returned only once, at creation time - the raw key is never
    retrievable again afterwards, same convention as any other API key
    issuance flow."""

    api_key: str
