import uuid

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func

from app.core.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class Video(Base):
    """Mirrors Photo's shape and lifecycle (draft/published/flagged,
    view/like counts, category/description/specs, admin CRUD) -- see
    Photo's own comments for why each of those fields exists, since the
    reasoning is identical here. Only genuinely video-specific fields are
    called out below; everything else is a deliberate 1:1 mirror so the
    two features stay easy to reason about together.

    Kept as its OWN table rather than a shared "media" table with a
    type discriminator: Photo is existing, tested, production-shaped
    code, and duration/poster/mime don't apply to photos at all -- a
    shared table would mean either nullable video-only columns on every
    photo row, or a single-table-inheritance layer neither the existing
    codebase nor its tests were built around. Comments/likes/views DO
    extend their existing tables (see Comment.video_id, VideoLike,
    VideoView below) rather than duplicating those, since that logic
    (rate limiting, notify-on-reply, dedup-by-viewer) is exactly the
    same for both media types and duplicating it risks drift.
    """

    __tablename__ = "videos"

    id = Column(String(36), primary_key=True, default=gen_uuid)

    object_key = Column(String(500), nullable=False, unique=True)
    # A user-supplied or (future) server-generated still frame shown in
    # gallery grids instead of the raw video -- without this, a video
    # tile would either need to autoplay/load video data just to render
    # a thumbnail (expensive, bad for a public gallery grid) or fall
    # back to a generic placeholder. Points at an object_key in the
    # PHOTOS bucket (posters are images, not videos), same public_url()
    # helper as Photo.object_key.
    poster_object_key = Column(String(500), nullable=True)

    title = Column(String(200), nullable=False)
    category = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=False, default="")
    specs = Column(JSON, nullable=False, default=list)  # list[str]

    status = Column(String(20), nullable=False, default="draft", index=True)  # draft | published | flagged

    # Video-specific: enforced server-side at upload time against
    # settings.MAX_VIDEO_DURATION_SECONDS (see the video upload
    # endpoint) -- stored so the gallery/admin UI can show it without
    # re-probing the file, and so the enforcement decision itself is
    # auditable after the fact.
    duration_seconds = Column(Float, nullable=False)
    mime_type = Column(String(100), nullable=False)

    view_count = Column(Integer, nullable=False, default=0)
    like_count = Column(Integer, nullable=False, default=0)

    uploaded_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class VideoLike(Base):
    """Same pattern as PhotoLike -- see its docstring."""

    __tablename__ = "video_likes"
    __table_args__ = (UniqueConstraint("video_id", "customer_id", name="uq_video_likes_video_customer"),)

    id = Column(String(36), primary_key=True, default=gen_uuid)
    video_id = Column(String(36), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class VideoView(Base):
    """Same pattern as PhotoView -- see its docstring."""

    __tablename__ = "video_views"
    __table_args__ = (UniqueConstraint("video_id", "viewer_key", name="uq_video_views_video_viewer"),)

    id = Column(String(36), primary_key=True, default=gen_uuid)
    video_id = Column(String(36), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)
    viewer_key = Column(String(255), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
