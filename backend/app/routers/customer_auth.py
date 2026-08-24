import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import CUSTOMER_COOKIE, get_current_customer
from app.core.email import send_verification_email
from app.core.ip import get_client_ip
from app.core.oauth_google import build_authorization_url, exchange_code_for_tokens, fetch_google_userinfo
from app.core.rate_limit import check_and_increment
from app.core.security import create_access_token, hash_password, verify_password
from app.core.security_log import log_security_event
from app.core.tokens import expiry_from_now, generate_raw_token, hash_token, utcnow
from app.core.turnstile import verify_turnstile_token
from app.models.auth_token import AuthToken
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    ResendVerificationRequest,
    UserOut,
    VerifyEmailRequest,
)

router = APIRouter(prefix="/api/customer", tags=["customer-auth"])

# Short-lived, separate from CUSTOMER_COOKIE -- only ever holds a random
# CSRF token during the ~seconds-long round trip to Google and back, never
# an identity. Cleared as soon as the callback consumes it.
OAUTH_STATE_COOKIE = "oauth_state"


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        avatarInitials=user.avatar_initials,
        emailVerified=user.email_verified,
    )


def _set_session_cookie(response: Response, user: User) -> None:
    settings = get_settings()
    token = create_access_token(subject=user.id, role=user.role)
    response.set_cookie(
        key=CUSTOMER_COOKIE,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )


@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    ip = get_client_ip(request)

    allowed, retry_after = await check_and_increment(
        f"rl:register:{ip}",
        settings.RATE_LIMIT_REGISTER_MAX_ATTEMPTS,
        settings.RATE_LIMIT_REGISTER_WINDOW_MINUTES * 60,
    )
    if not allowed:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, f"Too many attempts. Try again in {retry_after}s.")

    if not await verify_turnstile_token(payload.turnstile_token, ip):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Verification failed. Please try again.")

    email = payload.email.lower()
    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")

    user = User(
        email=email,
        name=payload.name.strip(),
        password_hash=hash_password(payload.password),
        role="customer",
        email_verified=False,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    raw_token = generate_raw_token()
    db.add(
        AuthToken(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            purpose="email_verify",
            expires_at=expiry_from_now(hours=settings.EMAIL_VERIFICATION_TOKEN_TTL_HOURS),
        )
    )
    await db.commit()

    await send_verification_email(user.email, raw_token)
    await log_security_event(
        db, "register", "success", user_id=user.id, ip_address=ip, user_agent=request.headers.get("user-agent")
    )

    return MessageResponse(message="Account created. Check your email to verify your address before signing in.")


@router.post("/verify-email", response_model=UserOut)
async def verify_email(
    payload: VerifyEmailRequest, response: Response, request: Request, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(AuthToken).where(AuthToken.token_hash == hash_token(payload.token), AuthToken.purpose == "email_verify")
    )
    auth_token = result.scalar_one_or_none()
    now = utcnow()

    if not auth_token or auth_token.used_at is not None or auth_token.expires_at < now:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This verification link is invalid or has expired.")

    result = await db.execute(select(User).where(User.id == auth_token.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This verification link is invalid or has expired.")

    user.email_verified = True
    auth_token.used_at = now
    await db.commit()
    await db.refresh(user)

    _set_session_cookie(response, user)
    await log_security_event(db, "email_verify", "success", user_id=user.id, ip_address=get_client_ip(request))

    return _user_out(user)


@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification(payload: ResendVerificationRequest, request: Request, db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    ip = get_client_ip(request)

    allowed, retry_after = await check_and_increment(
        f"rl:resend:{ip}",
        settings.RATE_LIMIT_REGISTER_MAX_ATTEMPTS,
        settings.RATE_LIMIT_REGISTER_WINDOW_MINUTES * 60,
    )
    if not allowed:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, f"Too many attempts. Try again in {retry_after}s.")

    # Always the same response whether or not the account exists / is
    # already verified, so this endpoint can't be used to enumerate emails.
    generic = MessageResponse(message="If that account exists and isn't verified yet, we've sent a new link.")

    result = await db.execute(select(User).where(User.email == payload.email.lower(), User.role == "customer"))
    user = result.scalar_one_or_none()
    if not user or user.email_verified:
        return generic

    raw_token = generate_raw_token()
    db.add(
        AuthToken(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            purpose="email_verify",
            expires_at=expiry_from_now(hours=settings.EMAIL_VERIFICATION_TOKEN_TTL_HOURS),
        )
    )
    await db.commit()
    await send_verification_email(user.email, raw_token)
    return generic


@router.post("/login", response_model=UserOut)
async def login(payload: LoginRequest, response: Response, request: Request, db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    ip = get_client_ip(request)

    allowed, retry_after = await check_and_increment(
        f"rl:login:customer:{ip}",
        settings.RATE_LIMIT_LOGIN_MAX_ATTEMPTS,
        settings.RATE_LIMIT_LOGIN_WINDOW_MINUTES * 60,
    )
    if not allowed:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, f"Too many attempts. Try again in {retry_after}s.")

    if not await verify_turnstile_token(payload.turnstile_token, ip):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Verification failed. Please try again.")

    result = await db.execute(select(User).where(User.email == payload.email.lower(), User.role == "customer"))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.password_hash):
        await log_security_event(
            db, "login", "failure", ip_address=ip, user_agent=request.headers.get("user-agent"),
            details=f"email={payload.email.lower()}",
        )
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account has been deactivated")

    if not user.email_verified:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Please verify your email before signing in")

    _set_session_cookie(response, user)
    await log_security_event(
        db, "login", "success", user_id=user.id, ip_address=ip, user_agent=request.headers.get("user-agent")
    )

    return _user_out(user)


@router.post("/logout", response_model=MessageResponse)
async def logout(response: Response):
    response.delete_cookie(CUSTOMER_COOKIE, path="/")
    return MessageResponse(message="Signed out")


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_customer)):
    return _user_out(user)


# ---- Google OAuth2 ("Sign in with Google") ----
#
# Both of these are meant to be hit via full browser navigation (an <a
# href> or window.location.href on the frontend), never fetch()/XHR --
# that's how OAuth redirect flows work. Post-proxy-migration, the login
# link is a relative /api/... path (same-origin via vercel.json/
# vite.config.ts), and GOOGLE_REDIRECT_URI points at the frontend's own
# domain too -- so the session cookie set on callback lands on the
# frontend's origin, consistent with every other login path.


@router.get("/oauth/google/login")
async def google_oauth_login():
    settings = get_settings()
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Google sign-in is not configured")

    state = generate_raw_token()
    redirect = RedirectResponse(build_authorization_url(state))
    redirect.set_cookie(
        key=OAUTH_STATE_COOKIE,
        value=state,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=600,  # the whole Google round trip should take seconds, not 10 minutes -- generous on purpose
        path="/",
    )
    return redirect


@router.get("/oauth/google/callback")
async def google_oauth_callback(request: Request, db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    frontend_url = settings.FRONTEND_URL.rstrip("/")

    code = request.query_params.get("code")
    state = request.query_params.get("state")
    cookie_state = request.cookies.get(OAUTH_STATE_COOKIE)

    # Missing/mismatched state means either a stale link, a direct hit on
    # this URL, or an actual CSRF attempt -- all get the same generic
    # bounce, no detail on which.
    if not code or not state or not cookie_state or not secrets.compare_digest(state, cookie_state):
        return RedirectResponse(f"{frontend_url}/login?error=oauth_failed")

    try:
        tokens = await exchange_code_for_tokens(code)
        userinfo = await fetch_google_userinfo(tokens["access_token"])
    except Exception:
        # Any failure talking to Google (expired code, network hiccup,
        # revoked consent mid-flow) is opaque to the person -- they just
        # see "something went wrong, try again" on the login page.
        return RedirectResponse(f"{frontend_url}/login?error=oauth_failed")

    google_id = userinfo.get("sub")
    email = (userinfo.get("email") or "").lower().strip()
    name = (userinfo.get("name") or "").strip() or (email.split("@")[0] if email else "Google User")

    if not google_id or not email:
        return RedirectResponse(f"{frontend_url}/login?error=oauth_failed")

    # 1. Already linked to this Google account -- straightforward login.
    result = await db.execute(select(User).where(User.google_id == google_id))
    user = result.scalar_one_or_none()

    if not user:
        # 2. Not linked yet -- does a password-based account already own
        # this email? Google has already verified the email address, so
        # linking here is safe: it's an addition (Google becomes a second
        # way in), never a takeover -- the original password keeps working.
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user:
            if user.role != "customer":
                # Never let a Google login attach to an admin/staff account
                # -- that side never authenticates this way, full stop.
                return RedirectResponse(f"{frontend_url}/login?error=oauth_failed")
            user.google_id = google_id
            if not user.email_verified:
                user.email_verified = True
        else:
            # 3. Brand new account. No password was ever chosen for it --
            # fill the NOT NULL column with a random value nobody knows and
            # verify_password() can never match, so password login stays
            # impossible until they deliberately set one via
            # forgot-password. They can still always sign in with Google.
            user = User(
                email=email,
                name=name,
                password_hash=hash_password(secrets.token_urlsafe(32)),
                role="customer",
                email_verified=True,
                is_active=True,
                google_id=google_id,
            )
            db.add(user)

    if not user.is_active:
        return RedirectResponse(f"{frontend_url}/login?error=account_disabled")

    await db.commit()
    await db.refresh(user)

    await log_security_event(
        db, "login", "success", user_id=user.id, ip_address=get_client_ip(request), details="method=google_oauth"
    )

    redirect = RedirectResponse(f"{frontend_url}/dashboard")
    redirect.delete_cookie(OAUTH_STATE_COOKIE, path="/")
    _set_session_cookie(redirect, user)  # RedirectResponse is a Response subclass -- same helper as password login
    return redirect
