"""
The SecurityLog model itself now lives in app/models/security_log.py --
see that file's docstring for why it was moved there (in short: a model
living in app/core/ was invisible to both Alembic's autogenerate and the
app's own DEBUG-mode table creation, both of which only scan
app/models/). This module keeps just the log_security_event() helper,
re-exporting SecurityLog for any existing import of
`app.core.security_log.SecurityLog` to keep working.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.security_log import SecurityLog  # noqa: F401 -- re-exported for backward compatibility


async def log_security_event(
    db: AsyncSession,
    event_type: str,
    event_status: str,
    user_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    details: str | None = None,
) -> None:
    """Best-effort logging -- never raises, never blocks the request it's observing."""
    try:
        entry = SecurityLog(
            user_id=user_id, event_type=event_type, event_status=event_status,
            ip_address=ip_address, user_agent=(user_agent[:500] if user_agent else None),
            details=details,
        )
        db.add(entry)
        await db.commit()
    except Exception:
        await db.rollback()
