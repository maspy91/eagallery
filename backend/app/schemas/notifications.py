# backend/app/schemas/notifications.py
# NEW FILE — place at: app/schemas/notifications.py

from typing import Literal

from pydantic import BaseModel

NotificationType = Literal["comment_reply", "conversation_reply", "system"]


class NotificationOut(BaseModel):
    # camelCase to match the frontend's AppNotification type (src/lib/types.ts).
    id: str
    userId: str
    type: NotificationType
    message: str
    href: str
    read: bool
    timestamp: str  # ISO 8601


class UnreadCountOut(BaseModel):
    count: int


class MessageResponse(BaseModel):
    message: str
