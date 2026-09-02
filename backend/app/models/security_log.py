"""
Was previously defined in app/core/security_log.py alongside the
log_security_event() helper function -- but app/models/__init__.py (used
by Alembic's autogenerate/migrations) and app/core/model_registry.py's
discover_models() (used by the app's own DEBUG-mode create_all() at
startup) BOTH only ever look at app/models/, not app/core/. A model
living in app/core/ was invisible to both, meaning the security_logs
table was never actually created outside of tests -- and tests only
"worked" because importing photos.py/videos.py/admin_auth.py/etc.
(which import log_security_event, which imported this class alongside
it) happened to register it on Base.metadata as an import side effect
before Base.metadata.create_all() ran in conftest.py.

Every log_security_event() call across the app (admin login, password
resets, email verification, customer login, photo/video uploads) was
silently failing and rolling back in any real deployment -- caught only
by log_security_event's own broad `except Exception: rollback` (see
app/core/security_log.py), with no error surfaced anywhere. Moving the
model here, where both discovery paths actually look, is the fix; a new
migration (see alembic/versions/) creates the table for real.
"""

import uuid

from sqlalchemy import Column, DateTime, String, Text, func

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
