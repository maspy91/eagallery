from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_customer
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notifications import MessageResponse, NotificationOut, UnreadCountOut

# Customer-only for now -- matches the frontend, where the bell only ever
# renders for the customer nav (Navbar.svelte's `isCustomer ? ... : 0`).
# Nothing here stops an admin/staff row existing later if that changes;
# there's just no trigger that creates one today.
router = APIRouter(prefix="/api/notifications", tags=["notifications"])


def _to_out(n: Notification) -> NotificationOut:
    return NotificationOut(
        id=n.id,
        userId=n.user_id,
        type=n.type,
        message=n.message,
        href=n.href,
        read=n.is_read,
        timestamp=n.created_at.isoformat() if n.created_at else "",
    )


@router.get("", response_model=list[NotificationOut])
async def list_notifications(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_customer)):
    result = await db.execute(
        select(Notification).where(Notification.user_id == user.id).order_by(Notification.created_at.desc())
    )
    return [_to_out(n) for n in result.scalars().all()]


@router.get("/unread-count", response_model=UnreadCountOut)
async def unread_count(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_customer)):
    """Lightweight endpoint for the Navbar badge -- avoids fetching and
    deserializing the full notification list just to render a number."""
    result = await db.execute(
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == user.id, Notification.is_read.is_(False))
    )
    return UnreadCountOut(count=result.scalar_one())


@router.post("/{notification_id}/read", response_model=NotificationOut)
async def mark_read(notification_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_customer)):
    result = await db.execute(
        select(Notification).where(Notification.id == notification_id, Notification.user_id == user.id)
    )
    notification = result.scalar_one_or_none()
    if not notification:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notification not found")

    notification.is_read = True
    await db.commit()
    await db.refresh(notification)
    return _to_out(notification)


@router.post("/read-all", response_model=MessageResponse)
async def mark_all_read(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_customer)):
    await db.execute(
        update(Notification)
        .where(Notification.user_id == user.id, Notification.is_read.is_(False))
        .values(is_read=True)
    )
    await db.commit()
    return MessageResponse(message="All notifications marked as read")
