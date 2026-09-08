from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

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
from app.models.photo import Photo, PhotoLike, PhotoView
from app.models.user import User
from app.schemas.photos import (
    LikeResponse,
    MessageResponse,
    PhotoCreateRequest,
    PhotoMetaOut,
    PhotoOut,
    PhotoStatsOut,
    PhotoUpdateRequest,
    UploadUrlRequest,
    UploadUrlResponse,
)

router = APIRouter(prefix="/api/photos", tags=["photos"])

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
VALID_STATUSES = {"draft", "published", "flagged"}


async def _photo_out(db: AsyncSession, photo: Photo, viewer: User | None) -> PhotoOut:
    liked = False
    if viewer is not None:
        result = await db.execute(
            select(PhotoLike).where(PhotoLike.photo_id == photo.id, PhotoLike.customer_id == viewer.id)
        )
        liked = result.scalar_one_or_none() is not None

    return PhotoOut(
        id=photo.id,
        image=public_url(photo.object_key),
        objectKey=photo.object_key,
        title=photo.title,
        category=photo.category,
        viewCount=photo.view_count,
        likeCount=photo.like_count,
        description=photo.description,
        specs=photo.specs or [],
        status=photo.status,
        liked=liked,
    )


# ---- Upload (admin/staff only, requires photos:manage) ----


@router.post(
    "/upload-url",
    response_model=UploadUrlResponse,
    dependencies=[Depends(require_permission("photos:manage"))],
)
async def get_upload_url(payload: UploadUrlRequest):
    """Step 1 of 2: the client PUTs the file directly to storage with the
    returned presigned URL -- the file's bytes never pass through this
    API server, only the (tiny) signed-URL request/response does. Step 2
    is POST /api/photos, once the direct upload has succeeded."""
    if payload.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unsupported file type")

    object_key = generate_object_key(payload.filename)
    # The storage SDK call is sync -- keep it off the event loop.
    upload_url = await run_in_threadpool(generate_presigned_upload_url, object_key, payload.content_type)

    return UploadUrlResponse(objectKey=object_key, uploadUrl=upload_url, publicUrl=public_url(object_key))


@router.post(
    "",
    response_model=PhotoOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("photos:manage"))],
)
async def create_photo(
    payload: PhotoCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    uploader: User = Depends(get_current_staff_or_admin),
):
    photo = Photo(
        object_key=payload.objectKey,
        title=payload.title.strip(),
        category=payload.category.strip(),
        description=payload.description.strip(),
        specs=payload.specs,
        status="draft",
        uploaded_by=uploader.id,
    )
    db.add(photo)
    await db.commit()
    await db.refresh(photo)

    await log_security_event(
        db, "photo_upload", "success", user_id=uploader.id, ip_address=get_client_ip(request),
        details=f"photo_id={photo.id}",
    )

    return await _photo_out(db, photo, uploader)


# ---- Read (public, with more visible to staff/admin) ----


def _apply_photo_filters(
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
        # Staff/admin may filter by any status (or see everything, unfiltered).
        if status_filter:
            if status_filter not in VALID_STATUSES:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid status filter")
            query = query.where(Photo.status == status_filter)
    else:
        # Everyone else only ever sees published photos, regardless of
        # what they pass in `status` -- this is the actual enforcement
        # point, not just a UI convenience.
        query = query.where(Photo.status == "published")

    if category:
        query = query.where(Photo.category == category)

    if q:
        like = f"%{q}%"
        query = query.where(or_(Photo.title.ilike(like), Photo.category.ilike(like), Photo.description.ilike(like)))

    parsed_from, parsed_to = parse_date_range(date_from, date_to)
    if parsed_from:
        query = query.where(Photo.created_at >= parsed_from)
    if parsed_to:
        query = query.where(Photo.created_at <= parsed_to)

    return query


@router.get("", response_model=list[PhotoOut])
async def list_photos(
    db: AsyncSession = Depends(get_db),
    viewer: User | None = Depends(get_optional_customer),
    staff_viewer: User | None = Depends(get_optional_staff_or_admin),
    status_filter: str | None = Query(default=None, alias="status"),
    category: str | None = Query(default=None),
    q: str | None = Query(default=None, max_length=255, description="Search by title, category, or description"),
    date_from: str | None = Query(default=None, description="YYYY-MM-DD, inclusive"),
    date_to: str | None = Query(default=None, description="YYYY-MM-DD, inclusive"),
    random: int | None = Query(default=None, ge=1, le=100, description="Return this many photos in random order"),
    limit: int = Query(default=50, ge=1, le=100),
):
    query = _apply_photo_filters(
        select(Photo),
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
        query = query.order_by(Photo.created_at.desc()).limit(limit)

    result = await db.execute(query)
    photos = result.scalars().all()

    return [await _photo_out(db, p, viewer) for p in photos]


@router.get(
    "/stats",
    response_model=PhotoStatsOut,
    dependencies=[Depends(require_permission("analytics:view"))],
)
async def get_photo_stats(db: AsyncSession = Depends(get_db)):
    """Single aggregate query (COUNT/SUM/FILTER) for the admin dashboard
    -- correct no matter how many photos exist, unlike deriving these
    numbers from a capped list() call on the frontend."""
    result = await db.execute(
        select(
            func.count().filter(Photo.status == "published"),
            func.coalesce(func.sum(Photo.view_count), 0),
            func.coalesce(func.sum(Photo.like_count), 0),
            func.count().filter(Photo.status == "flagged"),
        )
    )
    published_count, total_views, total_likes, flagged_count = result.one()
    return PhotoStatsOut(
        publishedCount=published_count,
        totalViews=total_views,
        totalLikes=total_likes,
        flaggedCount=flagged_count,
    )


@router.get("/export")
async def export_photos(
    db: AsyncSession = Depends(get_db),
    staff: User = Depends(require_permission("photos:manage")),
    status_filter: str | None = Query(default=None, alias="status"),
    category: str | None = Query(default=None),
    q: str | None = Query(default=None, max_length=255),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
):
    """CSV of photos matching the same filters as the list endpoint --
    admin/staff only (photos:manage). Reuses _apply_photo_filters with
    staff_viewer=staff so status_filter isn't restricted to
    published-only, same as list_photos already allows once a staff
    viewer is present."""
    query = _apply_photo_filters(
        select(Photo),
        staff_viewer=staff,
        status_filter=status_filter,
        category=category,
        q=q,
        date_from=date_from,
        date_to=date_to,
    )
    query = query.order_by(Photo.created_at.desc()).limit(EXPORT_ROW_LIMIT)

    result = await db.execute(query)
    photos = result.scalars().all()

    rows = (
        [
            p.id,
            p.title,
            p.category,
            p.status,
            str(p.view_count),
            str(p.like_count),
            p.created_at.isoformat() if p.created_at else "",
        ]
        for p in photos
    )
    return csv_response(
        "photos.csv", ["ID", "Title", "Category", "Status", "Views", "Likes", "Created At"], rows
    )


@router.get("/{photo_id}/meta", response_model=PhotoMetaOut)
async def get_photo_meta(photo_id: str, db: AsyncSession = Depends(get_db)):
    """Public, view-count-free. See PhotoMetaOut's docstring for why
    this exists as its own endpoint rather than reusing get_photo."""
    result = await db.execute(select(Photo).where(Photo.id == photo_id))
    photo = result.scalar_one_or_none()
    if not photo or photo.status != "published":
        # Same reasoning as get_photo -- 404, not 403, so a draft/flagged
        # photo's existence isn't leaked via this endpoint either.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Photo not found")

    return PhotoMetaOut(
        title=photo.title, description=photo.description, image=public_url(photo.object_key), category=photo.category
    )


@router.get("/{photo_id}", response_model=PhotoOut)
async def get_photo(
    photo_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    viewer: User | None = Depends(get_optional_customer),
    staff_viewer: User | None = Depends(get_optional_staff_or_admin),
):
    result = await db.execute(select(Photo).where(Photo.id == photo_id))
    photo = result.scalar_one_or_none()
    if not photo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Photo not found")

    if photo.status != "published" and staff_viewer is None:
        # Drafts and flagged photos don't exist as far as the public API
        # is concerned -- 404, not 403, so their existence isn't leaked.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Photo not found")

    if photo.status == "published":
        await _record_view_if_new(db, photo, viewer, staff_viewer, request)

    return await _photo_out(db, photo, viewer)


async def _record_view_if_new(
    db: AsyncSession, photo: Photo, viewer: User | None, staff_viewer: User | None, request: Request
) -> None:
    """Bumps Photo.view_count at most once per distinct viewer (see
    PhotoView's docstring for how 'distinct viewer' is defined). Wrapped
    in a SAVEPOINT + IntegrityError catch, not a check-then-insert,
    because two near-simultaneous requests from the same person (double
    tab, double click) could both pass a plain existence check before
    either commits -- the unique constraint is the real guard, this is
    just how to fail that gracefully instead of a 500."""
    if staff_viewer is not None:
        # Admin/staff previewing their own published photos shouldn't
        # inflate the public view count.
        return

    viewer_key = f"customer:{viewer.id}" if viewer is not None else f"ip:{get_client_ip(request)}"

    result = await db.execute(
        select(PhotoView.id).where(PhotoView.photo_id == photo.id, PhotoView.viewer_key == viewer_key)
    )
    if result.scalar_one_or_none() is not None:
        return  # already counted for this viewer

    try:
        async with db.begin_nested():  # SAVEPOINT -- rolls back just this insert on conflict, not the whole request
            db.add(PhotoView(photo_id=photo.id, viewer_key=viewer_key))
            await db.execute(update(Photo).where(Photo.id == photo.id).values(view_count=Photo.view_count + 1))
    except IntegrityError:
        # Lost the race to a concurrent request for the same viewer --
        # that request's insert already counted the view, nothing more to do.
        return

    await db.commit()
    await db.refresh(photo)


# ---- Write (admin/staff only, requires photos:manage) ----


@router.patch(
    "/{photo_id}",
    response_model=PhotoOut,
    dependencies=[Depends(require_permission("photos:manage"))],
)
async def update_photo(photo_id: str, payload: PhotoUpdateRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Photo).where(Photo.id == photo_id))
    photo = result.scalar_one_or_none()
    if not photo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Photo not found")

    updates = payload.model_dump(exclude_unset=True)
    if "title" in updates:
        photo.title = updates["title"].strip()
    if "category" in updates:
        photo.category = updates["category"].strip()
    if "description" in updates:
        photo.description = updates["description"].strip()
    if "specs" in updates:
        photo.specs = updates["specs"]
    if "status" in updates:
        photo.status = updates["status"]

    await db.commit()
    await db.refresh(photo)

    return await _photo_out(db, photo, None)


@router.delete(
    "/{photo_id}",
    response_model=MessageResponse,
    dependencies=[Depends(require_permission("photos:manage"))],
)
async def delete_photo(photo_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Photo).where(Photo.id == photo_id))
    photo = result.scalar_one_or_none()
    if not photo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Photo not found")

    object_key = photo.object_key
    await db.delete(photo)
    await db.commit()

    # Best-effort: the DB row is already gone (that's what makes the photo
    # disappear from the app), so a storage-side failure here shouldn't
    # turn into a 500 for something the user already sees as deleted -- it
    # just leaves an orphaned object in the bucket to clean up later.
    try:
        await run_in_threadpool(delete_object, object_key)
    except Exception:
        pass

    return MessageResponse(message="Photo deleted")


# ---- Likes (customer only) ----


@router.post("/{photo_id}/like", response_model=LikeResponse)
async def toggle_like(photo_id: str, db: AsyncSession = Depends(get_db), customer: User = Depends(get_current_customer)):
    result = await db.execute(select(Photo).where(Photo.id == photo_id, Photo.status == "published"))
    photo = result.scalar_one_or_none()
    if not photo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Photo not found")

    result = await db.execute(
        select(PhotoLike).where(PhotoLike.photo_id == photo_id, PhotoLike.customer_id == customer.id)
    )
    existing = result.scalar_one_or_none()

    if existing:
        await db.delete(existing)
        # No floor-at-0 clamp needed: this branch only runs when a like row
        # was found, so the counter can't have been at 0 already (barring
        # manual DB edits) -- and `func.max(0, ...)` isn't portable here
        # anyway (Postgres only has MAX as an aggregate, not a scalar
        # greatest-of-two; SQLite's is scalar -- they'd need different SQL).
        await db.execute(update(Photo).where(Photo.id == photo_id).values(like_count=Photo.like_count - 1))
        liked = False
    else:
        db.add(PhotoLike(photo_id=photo_id, customer_id=customer.id))
        await db.execute(update(Photo).where(Photo.id == photo_id).values(like_count=Photo.like_count + 1))
        liked = True

    await db.commit()
    await db.refresh(photo)

    return LikeResponse(liked=liked, likeCount=photo.like_count)
