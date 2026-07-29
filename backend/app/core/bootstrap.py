import logging

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.user import User

logger = logging.getLogger(__name__)


async def ensure_admin_bootstrap() -> None:
    """The ONLY way an admin account is ever created -- there is no public
    endpoint that grants the admin role. Set ADMIN_EMAIL/ADMIN_PASSWORD,
    deploy once, then either rotate the password via /forgot-password or
    remove the env vars (re-running with them set again is a no-op once
    the account exists)."""
    settings = get_settings()

    if not settings.ADMIN_EMAIL or not settings.ADMIN_PASSWORD:
        logger.info("Admin bootstrap skipped (ADMIN_EMAIL/ADMIN_PASSWORD not set)")
        return

    email = settings.ADMIN_EMAIL.lower()

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        existing = result.scalar_one_or_none()

        if existing:
            if existing.role != "admin":
                logger.warning("ADMIN_EMAIL matches an existing non-admin account -- bootstrap skipped")
            else:
                logger.info("Admin bootstrap: account already exists, nothing to do")
            return

        admin = User(
            email=email,
            name="Admin",
            password_hash=hash_password(settings.ADMIN_PASSWORD),
            role="admin",
            email_verified=True,
            is_active=True,
        )
        db.add(admin)
        await db.commit()
        logger.info(f"Bootstrapped admin account: {email}")
