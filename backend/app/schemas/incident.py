from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class IncidentCreate(BaseModel):
    request_id: Optional[int] = None
    severity: str = "low"  # low, medium, high, critical
    category: str
    summary: str
    impact: Optional[str] = None

class IncidentUpdate(BaseModel):
    severity: Optional[str] = None
    category: Optional[str] = None
    summary: Optional[str] = None
    impact: Optional[str] = None
    root_cause: Optional[str] = None
    status: Optional[str] = None

class IncidentOut(BaseModel):
    id: int
    org_id: int
    request_id: Optional[int]
    severity: str
    category: str
    summary: str
    impact: Optional[str]
    root_cause: Optional[str]
    status: str
    created_at: datetime
    resolved_at: Optional[datetime]
    
    class Config:
        from_attributes = True
