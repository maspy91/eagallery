from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

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
from app.models.photo import Photo, PhotoLike
from app.models.user import User
from app.schemas.photos import (
    LikeResponse,
    MessageResponse,
    PhotoCreateRequest,
    PhotoOut,
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
    """Step 1 of 2: the client PUTs the file directly to R2 with the
    returned presigned URL -- the file's bytes never pass through this API
    server, only the (tiny) signed-URL request/response does. Step 2 is
    POST /api/photos, once the direct upload has succeeded."""
    if payload.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unsupported file type")

    object_key = generate_object_key(payload.filename)
    # boto3 is sync -- keep it off the event loop (see app/core/storage.py).
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


@router.get("", response_model=list[PhotoOut])
async def list_photos(
    db: AsyncSession = Depends(get_db),
    viewer: User | None = Depends(get_optional_customer),
    staff_viewer: User | None = Depends(get_optional_staff_or_admin),
    status_filter: str | None = Query(default=None, alias="status"),
    category: str | None = Query(default=None),
    random: int | None = Query(default=None, ge=1, le=100, description="Return this many photos in random order"),
    limit: int = Query(default=50, ge=1, le=100),
):
    query = select(Photo)

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

    if random:
        query = query.order_by(func.random()).limit(random)
    else:
        query = query.order_by(Photo.created_at.desc()).limit(limit)

    result = await db.execute(query)
    photos = result.scalars().all()

    return [await _photo_out(db, p, viewer) for p in photos]


@router.get("/{photo_id}", response_model=PhotoOut)
async def get_photo(
    photo_id: str,
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
        # SQL-level increment (`view_count = view_count + 1`), not a
        # read-modify-write on the Python object -- avoids two concurrent
        # requests both reading N and both writing N+1 (losing a view).
        await db.execute(update(Photo).where(Photo.id == photo.id).values(view_count=Photo.view_count + 1))
        await db.commit()
        await db.refresh(photo)

    return await _photo_out(db, photo, viewer)


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
    # disappear from the app), so an R2-side failure here shouldn't turn
    # into a 500 for something the user already sees as deleted -- it just
    # leaves an orphaned object in the bucket to clean up later.
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
