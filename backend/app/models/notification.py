# backend/app/models/notification.py
# NEW FILE — place at: app/models/notification.py

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, func

from app.core.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class Notification(Base):
    """
    Created server-side only, from two trigger points: a reply to a
    comment (app/routers/comments.py) and an admin/staff reply to a
    business conversation (app/routers/conversations.py) -- see
    app/core/notifications.py for the shared creation helper. `type` is
    kept even though only two of its three values are ever produced right
    now ('system' has no trigger yet) -- matches the frontend's
    AppNotification union, which already reserves it.
    """

    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(30), nullable=False)  # comment_reply | conversation_reply | system
    message = Column(String(500), nullable=False)
    href = Column(String(500), nullable=False)
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
