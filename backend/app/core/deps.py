import jwt as pyjwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import has_permission
from app.core.security import decode_access_token
from app.models.user import User

# Two separate cookie names for two separate session systems -- a customer
# session cookie is never accepted on an admin route and vice versa, even
# if a token somehow validated against the wrong endpoint. Belt and
# suspenders on top of the role check inside the token payload itself.
CUSTOMER_COOKIE = "customer_session"
ADMIN_COOKIE = "admin_session"

_UNAUTHENTICATED = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


async def _resolve_user(request: Request, db: AsyncSession, cookie_name: str, allowed_roles: set[str]) -> User:
    token = request.cookies.get(cookie_name)
    if not token:
        raise _UNAUTHENTICATED

    try:
        payload = decode_access_token(token)
    except pyjwt.PyJWTError:
        raise _UNAUTHENTICATED

    user_id = payload.get("sub")
    role = payload.get("role")
    if not user_id or role not in allowed_roles:
        raise _UNAUTHENTICATED

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    # Re-check role against the live row, not just the token: if an admin
    # demotes a staff member mid-session, that staff member's already-issued
    # token stops working on the next request instead of staying valid
    # until natural expiry.
    if not user or not user.is_active or user.role != role:
        raise _UNAUTHENTICATED

    return user


async def get_current_customer(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    return await _resolve_user(request, db, CUSTOMER_COOKIE, {"customer"})


async def get_current_staff_or_admin(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    return await _resolve_user(request, db, ADMIN_COOKIE, {"admin", "staff"})


async def get_current_admin(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    return await _resolve_user(request, db, ADMIN_COOKIE, {"admin"})


def require_permission(permission: str):
    """Dependency factory: Depends(require_permission('roles:manage'))"""

    async def checker(user: User = Depends(get_current_staff_or_admin)) -> User:
        if not has_permission(user.role, permission):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return checker
