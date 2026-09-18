from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional, Literal


class DomainCatalogCreate(BaseModel):
    domain: str
    tool_name: Optional[str] = None
    category: Optional[str] = None
    policy_status: Literal["allowed", "blocked", "unknown"] = "unknown"

    @field_validator("domain")
    @classmethod
    def normalize_domain(cls, v: str) -> str:
        v = v.strip().lower()
        if not v:
            raise ValueError("domain must not be empty")
        return v


class DomainCatalogUpdate(BaseModel):
    tool_name: Optional[str] = None
    category: Optional[str] = None
    policy_status: Optional[Literal["allowed", "blocked", "unknown"]] = None


class DomainCatalogOut(BaseModel):
    id: int
    org_id: int
    domain: str
    tool_name: Optional[str]
    category: Optional[str]
    policy_status: str
    source: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
