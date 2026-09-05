from pydantic import BaseModel
from datetime import datetime

class OrganizationBase(BaseModel):
    name: str
    plan: str = "free"

class OrganizationCreate(OrganizationBase):
    pass

class OrganizationOut(OrganizationBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True
