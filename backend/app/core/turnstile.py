import logging

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


async def verify_turnstile_token(token: str | None, ip: str | None = None) -> bool:
    settings = get_settings()

    if not settings.TURNSTILE_ENABLED:
        return True

    if not token:
        return False

    data = {"secret": settings.TURNSTILE_SECRET, "response": token}
    if ip:
        data["remoteip"] = ip

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(TURNSTILE_VERIFY_URL, data=data)
            if resp.status_code != 200:
                logger.warning(f"Turnstile provider returned HTTP {resp.status_code}")
                return False
            return bool(resp.json().get("success", False))
    except Exception as e:
        logger.error(f"Turnstile provider error: {e}")
        return False