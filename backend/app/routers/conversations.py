from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_customer, get_optional_customer, get_optional_staff_or_admin, require_permission
from app.core.notifications import create_notification
from app.core.permissions import has_permission
from app.core.tokens import utcnow
from app.models.conversation import Conversation, ConversationMessage
from app.models.user import User
from app.schemas.conversations import (
    ConversationCreateRequest,
    ConversationMessageOut,
    ConversationOut,
    ConversationStatusRequest,
    MessageCreateRequest,
)

router = APIRouter(prefix="/api/conversations", tags=["conversations"])

# No dedicated rate limiter here, unlike comments -- both sides of this
# feature require an authenticated session (no anonymous/guest path), so
# the spam surface is much smaller. Revisit if abuse from a compromised
# account ever becomes a real concern.


async def _load_with_messages(db: AsyncSession, conversations: list[Conversation]) -> list[ConversationOut]:
    if not conversations:
        return []

    conv_ids = [c.id for c in conversations]
    result = await db.execute(
        select(ConversationMessage)
        .where(ConversationMessage.conversation_id.in_(conv_ids))
        .order_by(ConversationMessage.created_at.asc())
    )
    messages_by_conv: dict[str, list[ConversationMessage]] = {}
    for m in result.scalars().all():
        messages_by_conv.setdefault(m.conversation_id, []).append(m)

    return [
        ConversationOut(
            id=c.id,
            customerId=c.customer_id,
            customerName=c.customer_name,
            customerEmail=c.customer_email,
            subject=c.subject,
            status=c.status,
            updatedAt=c.updated_at.isoformat() if c.updated_at else "",
            messages=[
                ConversationMessageOut(
                    id=m.id,
                    senderRole=m.sender_role,
                    senderName=m.sender_name,
                    text=m.text,
                    timestamp=m.created_at.isoformat() if m.created_at else "",
                )
                for m in messages_by_conv.get(c.id, [])
            ],
        )
        for c in conversations
    ]


# ---- Customer: start + list own conversations ----


@router.post("", response_model=ConversationOut, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: ConversationCreateRequest,
    db: AsyncSession = Depends(get_db),
    customer: User = Depends(get_current_customer),
):
    conversation = Conversation(
        customer_id=customer.id,
        customer_name=customer.name,
        customer_email=customer.email,
        subject=payload.subject.strip(),
        status="new",
    )
    db.add(conversation)
    await db.flush()  # assigns conversation.id without a full commit yet

    message = ConversationMessage(
        conversation_id=conversation.id,
        sender_id=customer.id,
        sender_role="customer",
        sender_name=customer.name,
        text=payload.text.strip(),
    )
    db.add(message)
    await db.commit()
    await db.refresh(conversation)

    out = await _load_with_messages(db, [conversation])
    return out[0]


@router.get("/mine", response_model=list[ConversationOut])
async def list_my_conversations(db: AsyncSession = Depends(get_db), customer: User = Depends(get_current_customer)):
    result = await db.execute(
        select(Conversation).where(Conversation.customer_id == customer.id).order_by(Conversation.updated_at.desc())
    )
    return await _load_with_messages(db, list(result.scalars().all()))


# ---- Admin/staff: list everyone's conversations (requests:respond) ----


@router.get("", response_model=list[ConversationOut], dependencies=[Depends(require_permission("requests:respond"))])
async def list_all_conversations(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Conversation).order_by(Conversation.updated_at.desc()))
    return await _load_with_messages(db, list(result.scalars().all()))


@router.patch(
    "/{conversation_id}",
    response_model=ConversationOut,
    dependencies=[Depends(require_permission("requests:respond"))],
)
async def update_status(conversation_id: str, payload: ConversationStatusRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")

    conversation.status = payload.status
    conversation.updated_at = utcnow()
    await db.commit()
    await db.refresh(conversation)

    out = await _load_with_messages(db, [conversation])
    return out[0]


# ---- Shared: reply -- either the owning customer, or any admin/staff
# with requests:respond. Can't express "customer who owns this row OR
# staff with this permission" as a single Depends(), so both sides are
# resolved optionally and the branch happens in the body. ----


@router.post("/{conversation_id}/messages", response_model=ConversationOut)
async def add_message(
    conversation_id: str,
    payload: MessageCreateRequest,
    db: AsyncSession = Depends(get_db),
    customer: User | None = Depends(get_optional_customer),
    staff: User | None = Depends(get_optional_staff_or_admin),
):
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")

    if customer is not None and conversation.customer_id == customer.id:
        sender = customer
    elif staff is not None and has_permission(staff.role, "requests:respond"):
        sender = staff
    else:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized to reply to this conversation")

    message = ConversationMessage(
        conversation_id=conversation.id,
        sender_id=sender.id,
        sender_role=sender.role,
        sender_name=sender.name,
        text=payload.text.strip(),
    )
    db.add(message)

    conversation.updated_at = utcnow()
    # Matches the existing admin UI's behavior exactly: the first
    # admin/staff reply moves a fresh request out of "new" automatically;
    # resolving is still a separate, explicit action.
    if sender.role in ("admin", "staff") and conversation.status == "new":
        conversation.status = "in_progress"

    if sender.role in ("admin", "staff"):
        await create_notification(
            db,
            user_id=conversation.customer_id,
            type="conversation_reply",
            message=f"{sender.name} replied to your conversation: {conversation.subject}",
            href="/dashboard/inbox",
        )

    await db.commit()
    await db.refresh(conversation)

    out = await _load_with_messages(db, [conversation])
    return out[0]
