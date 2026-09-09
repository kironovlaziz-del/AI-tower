from pydantic import BaseModel, EmailStr
from datetime import datetime
from app.models.user import UserRole

class UserBase(BaseModel):
    email: EmailStr
    name: str
    role: UserRole = UserRole.user

class UserCreate(UserBase):
    password: str
    org_name: str

class UserOut(UserBase):
    id: int
    org_id: int
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

