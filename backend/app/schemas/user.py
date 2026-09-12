from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional
from app.models.user import UserRole


class UserBase(BaseModel):
    email: EmailStr
    name: str
    role: UserRole = UserRole.user


class UserCreate(UserBase):
    """First user of a new organization. Role is ignored server-side and
    forced to admin - see api/users.py."""
    password: str = Field(min_length=8)
    org_name: str


class UserInvite(BaseModel):
    """Admin inviting a teammate into an existing organization."""
    email: EmailStr
    name: str
    role: UserRole = UserRole.user
    password: str = Field(min_length=8)


class UserRoleUpdate(BaseModel):
    role: UserRole


class UserStatusUpdate(BaseModel):
    status: str = Field(pattern="^(active|disabled)$")


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


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
