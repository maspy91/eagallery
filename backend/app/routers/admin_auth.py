from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import ADMIN_COOKIE, get_current_staff_or_admin, require_permission
from app.core.email import send_password_reset_email, send_staff_invite_email
from app.core.ip import get_client_ip
from app.core.rate_limit import check_and_increment
from app.core.security import create_access_token, hash_password, verify_password
from app.core.security_log import log_security_event
from app.core.tokens import expiry_from_now, generate_raw_token, hash_token, is_expired, utcnow
from app.core.turnstile import verify_turnstile_token
from app.models.auth_token import AuthToken
from app.models.user import User
from app.schemas.auth import (
    AcceptInviteRequest,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    ResetPasswordRequest,
    StaffInviteRequest,
    UserOut,
)

# Admin/staff login + the two password-recovery endpoints shared with the
# customer side all live under /api/auth, matching the endpoint names
# already documented in the frontend's Phase-1 placeholder comments
# (src/routes/auth/+page.svelte, forgot-password/+page.svelte,
# reset-password/+page.svelte).
router = APIRouter(prefix="/api/auth", tags=["admin-auth"])


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        avatarInitials=user.avatar_initials,
        emailVerified=user.email_verified,
    )


def _set_admin_cookie(response: Response, user: User) -> None:
    settings = get_settings()
    token = create_access_token(subject=user.id, role=user.role)
    response.set_cookie(
        key=ADMIN_COOKIE,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )


# ---- Admin / staff login (entirely separate from customer login) ----


@router.post("/login", response_model=UserOut)
async def login(payload: LoginRequest, response: Response, request: Request, db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    ip = get_client_ip(request)

    allowed, retry_after = await check_and_increment(
        f"rl:login:admin:{ip}",
        settings.RATE_LIMIT_LOGIN_MAX_ATTEMPTS,
        settings.RATE_LIMIT_LOGIN_WINDOW_MINUTES * 60,
    )
    if not allowed:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, f"Too many attempts. Try again in {retry_after}s.")

    if not await verify_turnstile_token(payload.turnstile_token, ip):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Verification failed. Please try again.")

    result = await db.execute(
        select(User).where(User.email == payload.email.lower(), User.role.in_(["admin", "staff"]))
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.password_hash):
        await log_security_event(
            db, "admin_login", "failure", ip_address=ip, user_agent=request.headers.get("user-agent"),
            details=f"email={payload.email.lower()}",
        )
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account has been deactivated")

    _set_admin_cookie(response, user)
    await log_security_event(
        db, "admin_login", "success", user_id=user.id, ip_address=ip, user_agent=request.headers.get("user-agent")
    )

    return _user_out(user)


@router.post("/logout", response_model=MessageResponse)
async def logout(response: Response):
    response.delete_cookie(ADMIN_COOKIE, path="/")
    return MessageResponse(message="Signed out")


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_staff_or_admin)):
    return _user_out(user)


# ---- Password recovery -- shared by customer and admin/staff accounts,
# since it only ever needs an email address and doesn't care which side
# the account is on. ----


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(payload: ForgotPasswordRequest, request: Request, db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    ip = get_client_ip(request)

    allowed, retry_after = await check_and_increment(
        f"rl:forgot:{ip}",
        settings.RATE_LIMIT_LOGIN_MAX_ATTEMPTS,
        settings.RATE_LIMIT_LOGIN_WINDOW_MINUTES * 60,
    )
    if not allowed:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, f"Too many attempts. Try again in {retry_after}s.")

    # Same response regardless of whether the account exists -- this
    # endpoint must never be usable to enumerate registered emails.
    generic = MessageResponse(message="If an account with that email exists, we've sent a password reset link.")

    result = await db.execute(select(User).where(User.email == payload.email.lower()))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        return generic

    raw_token = generate_raw_token()
    db.add(
        AuthToken(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            purpose="password_reset",
            expires_at=expiry_from_now(minutes=settings.PASSWORD_RESET_TOKEN_TTL_MINUTES),
        )
    )
    await db.commit()

    await send_password_reset_email(user.email, raw_token)
    await log_security_event(db, "password_reset_requested", "success", user_id=user.id, ip_address=ip)

    return generic


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(payload: ResetPasswordRequest, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AuthToken).where(AuthToken.token_hash == hash_token(payload.token), AuthToken.purpose == "password_reset")
    )
    auth_token = result.scalar_one_or_none()
    now = utcnow()

    if not auth_token or auth_token.used_at is not None or is_expired(auth_token.expires_at, now):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This reset link is invalid or has expired.")

    result = await db.execute(select(User).where(User.id == auth_token.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This reset link is invalid or has expired.")

    user.password_hash = hash_password(payload.password)
    auth_token.used_at = now
    await db.commit()

    await log_security_event(db, "password_reset_completed", "success", user_id=user.id, ip_address=get_client_ip(request))

    # Deliberately no session cookie here -- resetting a password should
    # always require signing in again explicitly, not silently resume a
    # session for whoever is holding the reset link.
    return MessageResponse(message="Password updated. You can now sign in with your new password.")


# ---- Staff management -- admin only (roles:manage) ----


@router.post(
    "/staff/invite",
    response_model=MessageResponse,
    dependencies=[Depends(require_permission("roles:manage"))],
)
async def invite_staff(payload: StaffInviteRequest, db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    email = payload.email.lower()

    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")

    raw_token = generate_raw_token()
    db.add(
        AuthToken(
            email=email,
            token_hash=hash_token(raw_token),
            purpose="staff_invite",
            invite_name=payload.name.strip(),
            invite_role="staff",
            expires_at=expiry_from_now(hours=settings.EMAIL_VERIFICATION_TOKEN_TTL_HOURS),
        )
    )
    await db.commit()

    await send_staff_invite_email(email, raw_token)
    return MessageResponse(message=f"Invitation sent to {email}")


@router.post("/staff/accept-invite", response_model=UserOut)
async def accept_invite(payload: AcceptInviteRequest, response: Response, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AuthToken).where(AuthToken.token_hash == hash_token(payload.token), AuthToken.purpose == "staff_invite")
    )
    auth_token = result.scalar_one_or_none()
    now = utcnow()

    if not auth_token or auth_token.used_at is not None or is_expired(auth_token.expires_at, now):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This invite link is invalid or has expired.")

    existing = await db.execute(select(User).where(User.email == auth_token.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")

    user = User(
        email=auth_token.email,
        name=auth_token.invite_name or auth_token.email,
        password_hash=hash_password(payload.password),
        role=auth_token.invite_role or "staff",
        email_verified=True,
        is_active=True,
    )
    db.add(user)
    auth_token.used_at = now
    await db.commit()
    await db.refresh(user)

    _set_admin_cookie(response, user)
    return _user_out(user)


@router.get(
    "/staff",
    response_model=list[UserOut],
    dependencies=[Depends(require_permission("roles:manage"))],
)
async def list_staff(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.role == "staff").order_by(User.created_at.desc()))
    return [_user_out(u) for u in result.scalars().all()]


@router.delete(
    "/staff/{user_id}",
    response_model=MessageResponse,
    dependencies=[Depends(require_permission("roles:manage"))],
)
async def revoke_staff(user_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id, User.role == "staff"))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Staff member not found")

    await db.delete(user)
    await db.commit()
    return MessageResponse(message="Staff access revoked")
