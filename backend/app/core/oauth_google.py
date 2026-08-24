import httpx

from app.core.config import get_settings

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


def build_authorization_url(state: str) -> str:
    """The URL the browser gets redirected to -- Google shows its own
    consent screen, then redirects back to GOOGLE_REDIRECT_URI with a
    `code` and this same `state` value attached."""
    settings = get_settings()
    params = httpx.QueryParams(
        {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "online",
            "prompt": "select_account",
        }
    )
    return f"{GOOGLE_AUTH_URL}?{params}"


async def exchange_code_for_tokens(code: str) -> dict:
    """Server-to-server call -- the authorization code from the redirect
    is only good for one exchange, and this is the one place
    GOOGLE_CLIENT_SECRET is ever used. Raises on any non-2xx response
    (expired/reused code, mismatched redirect_uri, etc.) -- the caller
    treats that as an OAuth failure and redirects to the frontend's
    login page with an error, same as any other rejection in this flow."""
    settings = get_settings()
    data = {
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(GOOGLE_TOKEN_URL, data=data)
        resp.raise_for_status()
        return resp.json()


async def fetch_google_userinfo(access_token: str) -> dict:
    """Returns (at minimum) sub, email, email_verified, name -- see
    https://developers.google.com/identity/openid-connect/openid-connect#obtaininguserprofileinformation"""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(GOOGLE_USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"})
        resp.raise_for_status()
        return resp.json()
