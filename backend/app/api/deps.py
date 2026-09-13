from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.config import settings
from app.core.errors import api_error
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="auth.invalid_token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception

    # A user whose status has been flipped to anything other than "active"
    # is treated as deactivated: their existing JWT stops working even if
    # it has not expired yet.
    if user.status != "active":
        raise api_error(
            status.HTTP_403_FORBIDDEN,
            "auth.account_disabled",
            status=user.status,
        )

    return user


def require_role(*allowed: UserRole):
    """
    Dependency factory for role-based access control.

    Usage:
        @router.post("/...")
        async def endpoint(
            current_user: User = Depends(require_role(UserRole.admin)),
        ): ...

    The User.role column is a plain VARCHAR (see migration
    c3d5e7f9a1b4) so comparison is done against the .value of each role.
    """
    allowed_values = [r.value for r in allowed]

    async def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_values:
            raise api_error(
                status.HTTP_403_FORBIDDEN,
                "rbac.insufficient_role",
                allowed=allowed_values,
            )
        return current_user

    return checker
