import uuid

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func

from app.core.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class Photo(Base):
    __tablename__ = "photos"

    id = Column(String(36), primary_key=True, default=gen_uuid)

    # R2 object key, not the public URL -- the URL is derived from
    # R2_PUBLIC_URL + object_key at read time (see app/core/storage.py),
    # so changing the CDN/custom domain later doesn't require touching
    # every row.
    object_key = Column(String(500), nullable=False, unique=True)

    title = Column(String(200), nullable=False)
    category = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=False, default="")
    specs = Column(JSON, nullable=False, default=list)  # list[str]

    status = Column(String(20), nullable=False, default="draft", index=True)  # draft | published | flagged

    view_count = Column(Integer, nullable=False, default=0)
    like_count = Column(Integer, nullable=False, default=0)

    uploaded_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PhotoLike(Base):
    """One row per (photo, customer) -- existence is the like. Kept
    separate from Photo.like_count (a denormalized counter, cheap to read
    on every gallery card) so toggling a like is a simple insert/delete
    plus a +1/-1 on the counter, not a recount over the whole table."""

    __tablename__ = "photo_likes"
    __table_args__ = (UniqueConstraint("photo_id", "customer_id", name="uq_photo_likes_photo_customer"),)

    id = Column(String(36), primary_key=True, default=gen_uuid)
    photo_id = Column(String(36), ForeignKey("photos.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
