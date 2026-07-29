import uuid

from sqlalchemy import Column, DateTime, String, Text, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class SecurityLog(Base):
    __tablename__ = "security_logs"

    id = Column(String(36), primary_key=True, default=gen_uuid, index=True)
    user_id = Column(String(36), nullable=True, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    event_status = Column(String(30), nullable=False)
    ip_address = Column(String(45), nullable=True, index=True)
    user_agent = Column(Text, nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


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