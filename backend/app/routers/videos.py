from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.config import get_settings
from app.core.csv_export import EXPORT_ROW_LIMIT, csv_response, parse_date_range
from app.core.database import get_db
from app.core.deps import (
    get_current_customer,
    get_current_staff_or_admin,
    get_optional_customer,
    get_optional_staff_or_admin,
    require_permission,
)
from app.core.ip import get_client_ip
from app.core.security_log import log_security_event
from app.core.storage import delete_object, generate_object_key, generate_presigned_upload_url, public_url
from app.models.video import Video, VideoLike, VideoView
from app.models.user import User
from app.schemas.videos import (
    LikeResponse,
    MessageResponse,
    VideoCreateRequest,
    VideoMetaOut,
    VideoOut,
    VideoStatsOut,
    VideoUpdateRequest,
    VideoUploadUrlRequest,
    VideoUploadUrlResponse,
)

router = APIRouter(prefix="/api/videos", tags=["videos"])
settings = get_settings()

# A single, deliberately narrow format -- unlike photos (jpeg/png/webp/gif
# all render natively in every browser with no real downside to allowing
# all four), video format support varies enough across browsers that
# supporting more than one container here would mean either transcoding
# (explicitly out of scope -- no ffmpeg/job-queue infra in this app) or
# risking a video that uploads fine but won't play for some visitors.
# mp4 (H.264) is the one format every modern browser plays natively.
ALLOWED_CONTENT_TYPES = {"video/mp4"}
VALID_STATUSES = {"draft", "published", "flagged"}


async def _video_out(db: AsyncSession, video: Video, viewer: User | None) -> VideoOut:
    liked = False
    if viewer is not None:
        result = await db.execute(
            select(VideoLike).where(VideoLike.video_id == video.id, VideoLike.customer_id == viewer.id)
        )
        liked = result.scalar_one_or_none() is not None

    return VideoOut(
        id=video.id,
        video=public_url(video.object_key, bucket=settings.SUPABASE_VIDEO_BUCKET),
        objectKey=video.object_key,
        # The poster lives in the PHOTOS bucket (it's a still image, not a
        # video) -- see Video.poster_object_key's docstring.
        poster=public_url(video.poster_object_key) if video.poster_object_key else None,
        title=video.title,
        category=video.category,
        viewCount=video.view_count,
        likeCount=video.like_count,
        description=video.description,
        specs=video.specs or [],
        status=video.status,
        durationSeconds=video.duration_seconds,
        liked=liked,
    )


# ---- Upload (admin/staff only, requires photos:manage) ----
#
# Deliberately reuses the "photos:manage" permission rather than adding a
# new "videos:manage" one -- see app/core/permissions.py's ROLE_PERMISSIONS
# and the matching frontend copy in src/lib/types.ts. Every role that can
# manage photos today (admin, and staff granted that permission) should be
# able to manage videos too; splitting them into two separately-grantable
# permissions isn't something this feature needs, and doing it anyway would
# mean updating both the backend permission map and its frontend mirror,
# plus the staff invite/roles UI, for a distinction nobody asked for.


@router.post(
    "/upload-url",
    response_model=VideoUploadUrlResponse,
    dependencies=[Depends(require_permission("photos:manage"))],
)
async def get_upload_url(payload: VideoUploadUrlRequest):
    """Step 1 of 2, same shape as the photo upload flow (see
    photos.py's get_upload_url for the full explanation of why this is
    two steps) -- the file's bytes never pass through this API server.

    Unlike photos, this endpoint ALSO rejects on size/duration before
    issuing a presigned URL at all -- a fast, clear rejection for an
    honest client. This is NOT the real enforcement boundary though:
    that's the videos bucket's file_size_limit (see
    app/core/storage.py's ensure_bucket()), enforced by Supabase Storage
    itself on the direct browser upload that follows this call, which a
    client could skip straight to regardless of what it claims here.
    """
    if payload.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unsupported file type -- only MP4 video is accepted")

    if payload.size_bytes > settings.MAX_VIDEO_SIZE_BYTES:
        max_mb = settings.MAX_VIDEO_SIZE_BYTES / (1024 * 1024)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Video exceeds the {max_mb:.0f}MB size limit")

    if payload.duration_seconds > settings.MAX_VIDEO_DURATION_SECONDS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Video exceeds the {settings.MAX_VIDEO_DURATION_SECONDS}-second duration limit",
        )

    object_key = generate_object_key(payload.filename, prefix="videos")
    # The storage SDK call is sync -- keep it off the event loop.
    upload_url = await run_in_threadpool(
        generate_presigned_upload_url, object_key, payload.content_type, 300, settings.SUPABASE_VIDEO_BUCKET
    )

    return VideoUploadUrlResponse(
        objectKey=object_key,
        uploadUrl=upload_url,
        publicUrl=public_url(object_key, bucket=settings.SUPABASE_VIDEO_BUCKET),
    )


@router.post(
    "",
    response_model=VideoOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("photos:manage"))],
)
async def create_video(
    payload: VideoCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    uploader: User = Depends(get_current_staff_or_admin),
):
    # Duration is re-checked here against the value reported for the file
    # that actually finished uploading -- get_upload_url's check above
    # only saw a pre-upload claim, and duration (unlike size/MIME) has no
    # storage-service-level backstop the way the bucket's file_size_limit
    # backstops size. This is the last point this app can catch a
    # too-long video before it's live in the gallery.
    if payload.durationSeconds > settings.MAX_VIDEO_DURATION_SECONDS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Video exceeds the {settings.MAX_VIDEO_DURATION_SECONDS}-second duration limit",
        )
    if payload.mimeType not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unsupported file type -- only MP4 video is accepted")

    video = Video(
        object_key=payload.objectKey,
        poster_object_key=payload.posterObjectKey,
        title=payload.title.strip(),
        category=payload.category.strip(),
        description=payload.description.strip(),
        specs=payload.specs,
        duration_seconds=payload.durationSeconds,
        mime_type=payload.mimeType,
        status="draft",
        uploaded_by=uploader.id,
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)

    await log_security_event(
        db, "video_upload", "success", user_id=uploader.id, ip_address=get_client_ip(request),
        details=f"video_id={video.id}",
    )

    return await _video_out(db, video, uploader)


# ---- Read (public, with more visible to staff/admin) ----


def _apply_video_filters(
    query,
    *,
    staff_viewer: User | None,
    status_filter: str | None,
    category: str | None,
    q: str | None,
    date_from: str | None,
    date_to: str | None,
):
    if staff_viewer is not None:
        if status_filter:
            if status_filter not in VALID_STATUSES:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid status filter")
            query = query.where(Video.status == status_filter)
    else:
        query = query.where(Video.status == "published")

    if category:
        query = query.where(Video.category == category)

    if q:
        like = f"%{q}%"
        query = query.where(or_(Video.title.ilike(like), Video.category.ilike(like), Video.description.ilike(like)))

    parsed_from, parsed_to = parse_date_range(date_from, date_to)
    if parsed_from:
        query = query.where(Video.created_at >= parsed_from)
    if parsed_to:
        query = query.where(Video.created_at <= parsed_to)

    return query


@router.get("", response_model=list[VideoOut])
async def list_videos(
    db: AsyncSession = Depends(get_db),
    viewer: User | None = Depends(get_optional_customer),
    staff_viewer: User | None = Depends(get_optional_staff_or_admin),
    status_filter: str | None = Query(default=None, alias="status"),
    category: str | None = Query(default=None),
    q: str | None = Query(default=None, max_length=255, description="Search by title, category, or description"),
    date_from: str | None = Query(default=None, description="YYYY-MM-DD, inclusive"),
    date_to: str | None = Query(default=None, description="YYYY-MM-DD, inclusive"),
    random: int | None = Query(default=None, ge=1, le=100, description="Return this many videos in random order"),
    limit: int = Query(default=50, ge=1, le=100),
):
    query = _apply_video_filters(
        select(Video),
        staff_viewer=staff_viewer,
        status_filter=status_filter,
        category=category,
        q=q,
        date_from=date_from,
        date_to=date_to,
    )

    if random:
        query = query.order_by(func.random()).limit(random)
    else:
        query = query.order_by(Video.created_at.desc()).limit(limit)

    result = await db.execute(query)
    videos = result.scalars().all()

    return [await _video_out(db, v, viewer) for v in videos]


@router.get("/export")
async def export_videos(
    db: AsyncSession = Depends(get_db),
    staff: User = Depends(require_permission("photos:manage")),
    status_filter: str | None = Query(default=None, alias="status"),
    category: str | None = Query(default=None),
    q: str | None = Query(default=None, max_length=255),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
):
    """CSV of videos matching the same filters as the list endpoint.
    Gated by photos:manage, not a separate videos:manage permission --
    matches every other video-management endpoint in this router, which
    all reuse photos:manage rather than defining their own."""
    query = _apply_video_filters(
        select(Video),
        staff_viewer=staff,
        status_filter=status_filter,
        category=category,
        q=q,
        date_from=date_from,
        date_to=date_to,
    )
    query = query.order_by(Video.created_at.desc()).limit(EXPORT_ROW_LIMIT)

    result = await db.execute(query)
    videos = result.scalars().all()

    rows = (
        [
            v.id,
            v.title,
            v.category,
            v.status,
            str(v.view_count),
            str(v.like_count),
            v.created_at.isoformat() if v.created_at else "",
        ]
        for v in videos
    )
    return csv_response(
        "videos.csv", ["ID", "Title", "Category", "Status", "Views", "Likes", "Created At"], rows
    )


@router.get(
    "/stats",
    response_model=VideoStatsOut,
    dependencies=[Depends(require_permission("analytics:view"))],
)
async def get_video_stats(db: AsyncSession = Depends(get_db)):
    """Single aggregate query -- mirrors get_photo_stats in
    routers/photos.py exactly, same reasoning: correct no matter how
    many videos exist, unlike deriving these from a list() call."""
    result = await db.execute(
        select(
            func.count().filter(Video.status == "published"),
            func.coalesce(func.sum(Video.view_count), 0),
            func.coalesce(func.sum(Video.like_count), 0),
            func.count().filter(Video.status == "flagged"),
        )
    )
    published_count, total_views, total_likes, flagged_count = result.one()
    return VideoStatsOut(
        publishedCount=published_count,
        totalViews=total_views,
        totalLikes=total_likes,
        flaggedCount=flagged_count,
    )


@router.get("/{video_id}/meta", response_model=VideoMetaOut)
async def get_video_meta(video_id: str, db: AsyncSession = Depends(get_db)):
    """Public, view-count-free. See VideoMetaOut's docstring / the
    matching photos.py endpoint for why this exists separately."""
    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()
    if not video or video.status != "published":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Video not found")

    poster = public_url(video.poster_object_key) if video.poster_object_key else None
    return VideoMetaOut(title=video.title, description=video.description, image=poster, category=video.category)


@router.get("/{video_id}", response_model=VideoOut)
async def get_video(
    video_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    viewer: User | None = Depends(get_optional_customer),
    staff_viewer: User | None = Depends(get_optional_staff_or_admin),
):
    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Video not found")

    if video.status != "published" and staff_viewer is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Video not found")

    if video.status == "published":
        await _record_view_if_new(db, video, viewer, staff_viewer, request)

    return await _video_out(db, video, viewer)


async def _record_view_if_new(
    db: AsyncSession, video: Video, viewer: User | None, staff_viewer: User | None, request: Request
) -> None:
    """Same pattern as photos.py's _record_view_if_new -- see its
    docstring for the reasoning (dedup by viewer, SAVEPOINT + IntegrityError
    to handle the double-tab/double-click race)."""
    if staff_viewer is not None:
        return

    viewer_key = f"customer:{viewer.id}" if viewer is not None else f"ip:{get_client_ip(request)}"

    result = await db.execute(
        select(VideoView.id).where(VideoView.video_id == video.id, VideoView.viewer_key == viewer_key)
    )
    if result.scalar_one_or_none() is not None:
        return

    try:
        async with db.begin_nested():
            db.add(VideoView(video_id=video.id, viewer_key=viewer_key))
            await db.execute(update(Video).where(Video.id == video.id).values(view_count=Video.view_count + 1))
    except IntegrityError:
        return

    await db.commit()
    await db.refresh(video)


# ---- Write (admin/staff only, requires photos:manage) ----


@router.patch(
    "/{video_id}",
    response_model=VideoOut,
    dependencies=[Depends(require_permission("photos:manage"))],
)
async def update_video(video_id: str, payload: VideoUpdateRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Video not found")

    updates = payload.model_dump(exclude_unset=True)
    if "title" in updates:
        video.title = updates["title"].strip()
    if "category" in updates:
        video.category = updates["category"].strip()
    if "description" in updates:
        video.description = updates["description"].strip()
    if "specs" in updates:
        video.specs = updates["specs"]
    if "status" in updates:
        video.status = updates["status"]
    if "posterObjectKey" in updates:
        video.poster_object_key = updates["posterObjectKey"]

    await db.commit()
    await db.refresh(video)

    return await _video_out(db, video, None)


@router.delete(
    "/{video_id}",
    response_model=MessageResponse,
    dependencies=[Depends(require_permission("photos:manage"))],
)
async def delete_video(video_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Video not found")

    object_key = video.object_key
    poster_object_key = video.poster_object_key
    await db.delete(video)
    await db.commit()

    # Best-effort, same reasoning as photos.py's delete_photo: the DB row
    # is already gone (that's what makes it disappear from the app), so a
    # storage-side failure shouldn't turn into a 500 here.
    try:
        await run_in_threadpool(delete_object, object_key, settings.SUPABASE_VIDEO_BUCKET)
    except Exception:
        pass
    if poster_object_key:
        try:
            await run_in_threadpool(delete_object, poster_object_key)
        except Exception:
            pass

    return MessageResponse(message="Video deleted")


# ---- Likes (customer only) ----


@router.post("/{video_id}/like", response_model=LikeResponse)
async def toggle_like(video_id: str, db: AsyncSession = Depends(get_db), customer: User = Depends(get_current_customer)):
    result = await db.execute(select(Video).where(Video.id == video_id, Video.status == "published"))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Video not found")

    result = await db.execute(
        select(VideoLike).where(VideoLike.video_id == video_id, VideoLike.customer_id == customer.id)
    )
    existing = result.scalar_one_or_none()

    if existing:
        await db.delete(existing)
        await db.execute(update(Video).where(Video.id == video_id).values(like_count=Video.like_count - 1))
        liked = False
    else:
        db.add(VideoLike(video_id=video_id, customer_id=customer.id))
        await db.execute(update(Video).where(Video.id == video_id).values(like_count=Video.like_count + 1))
        liked = True

    await db.commit()
    await db.refresh(video)

    return LikeResponse(liked=liked, likeCount=video.like_count)
