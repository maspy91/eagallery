"""
Identifies an anonymous chat visitor across multiple messages in one
browser without requiring an account -- a random opaque token in its own
cookie, distinct from CUSTOMER_COOKIE/ADMIN_COOKIE (deps.py). Unlike
those, this cookie carries no auth claim at all (no JWT, no role, nothing
that grants access to anything else) -- it's purely "which
ChatThread.guest_token row is this browser's", so there's no meaningful
security boundary to defend here the way there is for a real session
token. A guest who clears cookies simply starts a new, unrelated thread
next time; that's an acceptable, expected loss of continuity for an
anonymous chat, not a bug.
"""

import secrets

from fastapi import Request, Response

from app.core.config import get_settings

GUEST_CHAT_COOKIE = "chat_guest_token"


def get_or_create_guest_token(request: Request, response: Response) -> str:
    existing = request.cookies.get(GUEST_CHAT_COOKIE)
    if existing:
        return existing

    settings = get_settings()
    token = secrets.token_urlsafe(32)
    response.set_cookie(
        key=GUEST_CHAT_COOKIE,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        # Deliberately much longer-lived than the auth session cookies --
        # there's no security reason to expire it quickly (see the
        # module docstring: it carries no auth claim), and a visitor
        # returning days later to continue a chat is a better experience
        # than losing thread continuity on every session cookie expiry.
        max_age=60 * 60 * 24 * 365,
        path="/",
    )
    return token
