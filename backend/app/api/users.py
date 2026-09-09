from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import get_password_hash
from app.schemas.user import UserCreate, UserOut
from app.models.user import User
from app.models.organization import Organization
from app.services.audit_service import AuditService
from app.api.deps import get_current_user

router = APIRouter()

@router.post("/register", response_model=UserOut)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    # Check if email exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    # Create organization
    org = Organization(name=user_data.org_name)
    db.add(org)
    await db.flush()
    
    # Create user
    user = User(
        org_id=org.id,
        email=user_data.email,
        name=user_data.name,
        hashed_password=get_password_hash(user_data.password),
        role=user_data.role
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    await AuditService(db).log(
        org.id, user.id, "organization", org.id, "created",
        {"org_name": org.name},
    )
    await AuditService(db).log(
        org.id, user.id, "user", user.id, "registered",
        {"email": user.email, "role": user.role.value if hasattr(user.role, "value") else user.role},
    )

    return user

@router.get("/me", response_model=UserOut)
async def get_me(
    current_user: User = Depends(get_current_user)
):
    return current_user
