import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, func

from app.core.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class Conversation(Base):
    """
    One thread shared between one customer and the platform's admin/staff
    -- the customer sees it in their dashboard Inbox, admin/staff see the
    exact same thread in Admin > Requests. There's only one copy of the
    data; a reply from either side just appends a ConversationMessage.

    customer_name/customer_email are a snapshot taken at creation time
    (same reasoning as Comment.author_name) -- a later name change doesn't
    rewrite the thread's history, and it avoids a join back to `users` on
    every list fetch.
    """

    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    customer_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_name = Column(String(100), nullable=False)
    customer_email = Column(String(255), nullable=False)

    subject = Column(String(200), nullable=False)
    status = Column(String(20), nullable=False, default="new", index=True)  # new | in_progress | resolved

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ConversationMessage(Base):
    """
    sender_name/sender_role are also a snapshot (not a live join to User)
    for the same reason as Comment.author_name -- and because sender_role
    specifically needs to reflect what the sender WAS at send time (e.g. a
    staff member later revoked shouldn't retroactively relabel their past
    replies)."""

    __tablename__ = "conversation_messages"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    sender_role = Column(String(20), nullable=False)  # customer | admin | staff
    sender_name = Column(String(100), nullable=False)

    text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
