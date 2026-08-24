from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification


async def create_notification(db: AsyncSession, *, user_id: str, type: str, message: str, href: str) -> None:
    """Adds the row to the session but doesn't commit -- callers already
    have their own commit at the end of the request (the comment/message
    that triggered this notification is being saved in the same
    transaction), so this stays a single round trip rather than two."""
    db.add(Notification(user_id=user_id, type=type, message=message[:500], href=href))
