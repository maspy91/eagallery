from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_optional_customer, require_permission
from app.core.ip import get_client_ip
from app.core.notifications import create_notification
from app.core.rate_limit import check_and_increment
from app.models.comment import Comment
from app.models.photo import Photo
from app.models.video import Video
from app.models.user import User
from app.schemas.comments import AdminCommentOut, CommentCreateRequest, CommentOut, MessageResponse, ModerateCommentRequest

# Three routers, same file: one nested under /api/photos/{photo_id}/comments
# and one under /api/videos/{video_id}/comments (public read + create, each
# scoped to one media item -- mirrors the tree shape the frontend already
# renders for either), one at /api/comments (moderation, cross-media, flat --
# mirrors the admin "Comments" page, which lists every comment in the
# gallery regardless of which photo/video it's on). The photo and video
# routers share the same handler bodies via the _comments_for_media helpers
# below rather than being copy-pasted, so a future change to rate limiting,
# tree-building, or notify-on-reply only has to happen once.
photo_comments_router = APIRouter(prefix="/api/photos", tags=["comments"])
video_comments_router = APIRouter(prefix="/api/videos", tags=["comments"])
moderation_router = APIRouter(prefix="/api/comments", tags=["comments"])

# Self-contained rate limit for comment posting -- deliberately not reusing
# RATE_LIMIT_REGISTER_* from settings (registration and commenting have very
# different natural rates; a genuinely engaged commenter can easily exceed
# a register-sized limit). Kept as local constants rather than new Settings
# fields to avoid touching config.py/.env for this feature. Shared by both
# photo and video comments -- one combined budget per IP, not double the
# effective rate via two separate buckets.
COMMENT_RATE_LIMIT_MAX_ATTEMPTS = 10
COMMENT_RATE_LIMIT_WINDOW_SECONDS = 600  # 10 minutes


def _to_out(comment: Comment, children_by_parent: dict[str | None, list[Comment]]) -> CommentOut:
    return CommentOut(
        id=comment.id,
        author=comment.author_name,
        authorId=comment.author_id,
        text=comment.text,
        timestamp=comment.created_at.isoformat() if comment.created_at else "",
        flagged=comment.is_flagged,
        replies=[_to_out(c, children_by_parent) for c in children_by_parent.get(comment.id, [])],
    )


def _build_tree(comments: list[Comment]) -> list[CommentOut]:
    children_by_parent: dict[str | None, list[Comment]] = {}
    for c in comments:
        children_by_parent.setdefault(c.parent_id, []).append(c)
    return [_to_out(c, children_by_parent) for c in children_by_parent.get(None, [])]


async def _collect_descendant_ids(db: AsyncSession, comment_id: str) -> list[str]:
    """All comments on one photo/video are a small, bounded set (unlike,
    say, photos or users), so a few extra round trips here to
    recursively gather reply ids before deleting is simpler and more
    portable across SQLite (tests) and Postgres (prod) than relying on
    FK cascade behavior, which SQLite doesn't enforce without an extra
    PRAGMA."""
    ids = [comment_id]
    frontier = [comment_id]
    while frontier:
        result = await db.execute(select(Comment.id).where(Comment.parent_id.in_(frontier)))
        next_ids = [row[0] for row in result.all()]
        ids.extend(next_ids)
        frontier = next_ids
    return ids


async def _list_comments_for(db: AsyncSession, *, photo_id: str | None, video_id: str | None) -> list[CommentOut]:
    media_col = Comment.photo_id if photo_id is not None else Comment.video_id
    media_id = photo_id if photo_id is not None else video_id
    result = await db.execute(select(Comment).where(media_col == media_id).order_by(Comment.created_at.asc()))
    return _build_tree(list(result.scalars().all()))


async def _create_comment_for(
    db: AsyncSession,
    request: Request,
    payload: CommentCreateRequest,
    commenter: User | None,
    *,
    photo_id: str | None,
    video_id: str | None,
    media_title: str,
    media_href: str,
) -> CommentOut:
    ip = get_client_ip(request)
    allowed, retry_after = await check_and_increment(
        f"rl:comment:{ip}", COMMENT_RATE_LIMIT_MAX_ATTEMPTS, COMMENT_RATE_LIMIT_WINDOW_SECONDS
    )
    if not allowed:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, f"Too many comments. Try again in {retry_after}s.")

    media_col = Comment.photo_id if photo_id is not None else Comment.video_id
    media_id = photo_id if photo_id is not None else video_id

    parent: Comment | None = None
    if payload.parent_id:
        result = await db.execute(select(Comment).where(Comment.id == payload.parent_id, media_col == media_id))
        parent = result.scalar_one_or_none()
        if parent is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid parent comment")

    comment = Comment(
        photo_id=photo_id,
        video_id=video_id,
        parent_id=payload.parent_id,
        author_id=commenter.id if commenter else None,
        author_name=commenter.name if commenter else "Anonymous User",
        text=payload.text.strip(),
        is_flagged=False,
    )
    db.add(comment)

    # Notify the parent comment's author -- only if they have an account
    # (guests have nowhere to receive a notification) and aren't replying
    # to themselves.
    if parent is not None and parent.author_id and parent.author_id != comment.author_id:
        replier_name = commenter.name if commenter else "Anonymous User"
        await create_notification(
            db,
            user_id=parent.author_id,
            type="comment_reply",
            message=f"{replier_name} replied to your comment on {media_title}",
            href=media_href,
        )

    await db.commit()
    await db.refresh(comment)

    return _to_out(comment, {})


# ---- Public: read + create, scoped to one photo ----


@photo_comments_router.get("/{photo_id}/comments", response_model=list[CommentOut])
async def list_photo_comments(photo_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Photo.id).where(Photo.id == photo_id, Photo.status == "published"))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Photo not found")
    return await _list_comments_for(db, photo_id=photo_id, video_id=None)


@photo_comments_router.post("/{photo_id}/comments", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
async def create_photo_comment(
    photo_id: str,
    payload: CommentCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    commenter: User | None = Depends(get_optional_customer),
):
    result = await db.execute(
        select(Photo.id, Photo.title).where(Photo.id == photo_id, Photo.status == "published")
    )
    photo_row = result.first()
    if photo_row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Photo not found")

    return await _create_comment_for(
        db, request, payload, commenter,
        photo_id=photo_id, video_id=None,
        media_title=photo_row.title, media_href=f"/image/{photo_id}",
    )


# ---- Public: read + create, scoped to one video ----


@video_comments_router.get("/{video_id}/comments", response_model=list[CommentOut])
async def list_video_comments(video_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Video.id).where(Video.id == video_id, Video.status == "published"))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Video not found")
    return await _list_comments_for(db, photo_id=None, video_id=video_id)


@video_comments_router.post("/{video_id}/comments", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
async def create_video_comment(
    video_id: str,
    payload: CommentCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    commenter: User | None = Depends(get_optional_customer),
):
    result = await db.execute(
        select(Video.id, Video.title).where(Video.id == video_id, Video.status == "published")
    )
    video_row = result.first()
    if video_row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Video not found")

    return await _create_comment_for(
        db, request, payload, commenter,
        photo_id=None, video_id=video_id,
        media_title=video_row.title, media_href=f"/video/{video_id}",
    )


# ---- Moderation: admin/staff, cross-media, flat (comments:moderate) ----


@moderation_router.get("", response_model=list[AdminCommentOut], dependencies=[Depends(require_permission("comments:moderate"))])
async def list_all_comments(db: AsyncSession = Depends(get_db)):
    # Two queries (photo comments, video comments) merged and re-sorted in
    # Python rather than one SQL UNION -- keeps each query a simple join
    # against its own media table (mirrors how the two create/list
    # endpoints above are already split), and the combined comment count
    # across a whole gallery is small enough that sorting client-side
    # here costs nothing meaningful.
    photo_result = await db.execute(
        select(Comment, Photo.title)
        .join(Photo, Photo.id == Comment.photo_id)
        .order_by(Comment.created_at.desc())
    )
    video_result = await db.execute(
        select(Comment, Video.title)
        .join(Video, Video.id == Comment.video_id)
        .order_by(Comment.created_at.desc())
    )

    out = [
        AdminCommentOut(
            id=comment.id, author=comment.author_name, authorId=comment.author_id,
            text=comment.text, timestamp=comment.created_at.isoformat() if comment.created_at else "",
            flagged=comment.is_flagged, replies=[],
            photoId=comment.photo_id, photoTitle=title,
        )
        for comment, title in photo_result.all()
    ] + [
        AdminCommentOut(
            id=comment.id, author=comment.author_name, authorId=comment.author_id,
            text=comment.text, timestamp=comment.created_at.isoformat() if comment.created_at else "",
            flagged=comment.is_flagged, replies=[],
            videoId=comment.video_id, videoTitle=title,
        )
        for comment, title in video_result.all()
    ]
    out.sort(key=lambda c: c.timestamp, reverse=True)
    return out


@moderation_router.patch(
    "/{comment_id}", response_model=MessageResponse, dependencies=[Depends(require_permission("comments:moderate"))]
)
async def moderate_comment(comment_id: str, payload: ModerateCommentRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Comment).where(Comment.id == comment_id))
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Comment not found")

    comment.is_flagged = payload.flagged
    await db.commit()
    return MessageResponse(message="Comment updated")


@moderation_router.delete(
    "/{comment_id}", response_model=MessageResponse, dependencies=[Depends(require_permission("comments:moderate"))]
)
async def delete_comment(comment_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Comment.id).where(Comment.id == comment_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Comment not found")

    ids_to_delete = await _collect_descendant_ids(db, comment_id)
    await db.execute(Comment.__table__.delete().where(Comment.id.in_(ids_to_delete)))
    await db.commit()

    return MessageResponse(message="Comment deleted")
