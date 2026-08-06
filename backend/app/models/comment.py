# backend/app/models/comment.py
# NEW FILE — place at: app/models/comment.py

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text, func

from app.core.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class Comment(Base):
    """
    Self-referential tree via parent_id (top-level comments have
    parent_id=None; replies point at the comment they're replying to).
    Nesting depth isn't enforced here -- the frontend caps display depth
    at 3 (see CommentItem.svelte's maxDepth); the backend just stores
    whatever parent_id it's given, as long as it belongs to the same photo.

    author_id is nullable: comments are allowed from guests (no login),
    matching the existing UI copy ("Posting as a guest..."). author_name
    is a snapshot taken at post time, not a live join to User -- so a
    later name change doesn't rewrite history, and guest comments (which
    have no User row at all) still have somewhere to store "Anonymous
    User".
    """

    __tablename__ = "comments"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    photo_id = Column(String(36), ForeignKey("photos.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_id = Column(String(36), ForeignKey("comments.id", ondelete="CASCADE"), nullable=True, index=True)
    author_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    author_name = Column(String(100), nullable=False)

    text = Column(Text, nullable=False)
    is_flagged = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
