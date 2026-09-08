import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.csv_export import EXPORT_ROW_LIMIT, csv_response, parse_date_range
from app.core.database import get_db
from app.core.deps import (
    get_current_customer,
    get_optional_customer,
    get_optional_staff_or_admin,
    require_permission,
)
from app.core.email import format_money, send_conversation_reply_email, send_quote_email
from app.core.notifications import create_notification
from app.core.permissions import has_permission
from app.core.tokens import utcnow
from app.models.conversation import Conversation, ConversationMessage, ConversationQuote
from app.models.user import User
from app.schemas.conversations import (
    ConversationCreateRequest,
    ConversationMessageOut,
    ConversationOut,
    ConversationStatsOut,
    ConversationStatusRequest,
    MessageCreateRequest,
    QuoteCreateRequest,
    QuoteOut,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/conversations", tags=["conversations"])

# No dedicated rate limiter here, unlike comments -- both sides of this
# feature require an authenticated session (no anonymous/guest path), so
# the spam surface is much smaller. Revisit if abuse from a compromised
# account ever becomes a real concern.


def _quote_out(q: ConversationQuote) -> QuoteOut:
    return QuoteOut(
        id=q.id,
        conversationId=q.conversation_id,
        createdByName=q.created_by_name,
        description=q.description,
        amountCents=q.amount_cents,
        currency=q.currency,
        status=q.status,
        createdAt=q.created_at.isoformat() if q.created_at else "",
        respondedAt=q.responded_at.isoformat() if q.responded_at else None,
    )


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

    quotes_result = await db.execute(
        select(ConversationQuote)
        .where(ConversationQuote.conversation_id.in_(conv_ids))
        .order_by(ConversationQuote.created_at.asc())
    )
    quotes_by_conv: dict[str, list[ConversationQuote]] = {}
    for q in quotes_result.scalars().all():
        quotes_by_conv.setdefault(q.conversation_id, []).append(q)

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
            quotes=[_quote_out(q) for q in quotes_by_conv.get(c.id, [])],
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


def _apply_conversation_filters(query, *, q: str | None, date_from: str | None, date_to: str | None):
    if q:
        like = f"%{q}%"
        query = query.where(
            or_(Conversation.subject.ilike(like), Conversation.customer_name.ilike(like), Conversation.customer_email.ilike(like))
        )

    parsed_from, parsed_to = parse_date_range(date_from, date_to)
    if parsed_from:
        query = query.where(Conversation.created_at >= parsed_from)
    if parsed_to:
        query = query.where(Conversation.created_at <= parsed_to)

    return query


@router.get("", response_model=list[ConversationOut], dependencies=[Depends(require_permission("requests:respond"))])
async def list_all_conversations(
    db: AsyncSession = Depends(get_db),
    q: str | None = Query(default=None, max_length=255, description="Search by subject, customer name, or email"),
    date_from: str | None = Query(default=None, description="YYYY-MM-DD, inclusive"),
    date_to: str | None = Query(default=None, description="YYYY-MM-DD, inclusive"),
):
    query = _apply_conversation_filters(
        select(Conversation).order_by(Conversation.updated_at.desc()), q=q, date_from=date_from, date_to=date_to
    )
    result = await db.execute(query)
    return await _load_with_messages(db, list(result.scalars().all()))


@router.get("/export", dependencies=[Depends(require_permission("requests:respond"))])
async def export_conversations(
    db: AsyncSession = Depends(get_db),
    q: str | None = Query(default=None, max_length=255),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
):
    """CSV of conversations matching the same filters as the list
    endpoint. Deliberately a lighter query than list_all_conversations --
    a CSV row doesn't need every message/quote in the thread, just the
    thread's own summary fields, so this skips _load_with_messages
    entirely rather than fetching all that just to discard it."""
    query = _apply_conversation_filters(
        select(Conversation).order_by(Conversation.created_at.desc()).limit(EXPORT_ROW_LIMIT),
        q=q, date_from=date_from, date_to=date_to,
    )
    result = await db.execute(query)
    conversations = result.scalars().all()

    rows = (
        [
            c.id,
            c.subject,
            c.customer_name,
            c.customer_email,
            c.status,
            c.created_at.isoformat() if c.created_at else "",
            c.updated_at.isoformat() if c.updated_at else "",
        ]
        for c in conversations
    )
    return csv_response(
        "conversations.csv",
        ["ID", "Subject", "Customer Name", "Customer Email", "Status", "Created At", "Updated At"],
        rows,
    )


@router.get(
    "/stats",
    response_model=ConversationStatsOut,
    dependencies=[Depends(require_permission("requests:respond"))],
)
async def get_conversation_stats(db: AsyncSession = Depends(get_db)):
    """Open (non-resolved) conversation count via SQL COUNT -- avoids
    list_all_conversations()'s full fetch-every-conversation-and-every-
    message-in-them just to take one number off the result for the admin
    dashboard overview."""
    result = await db.execute(
        select(func.count()).select_from(Conversation).where(Conversation.status != "resolved")
    )
    return ConversationStatsOut(openCount=result.scalar_one())


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

    notify_email: str | None = None
    if sender.role in ("admin", "staff"):
        await create_notification(
            db,
            user_id=conversation.customer_id,
            type="conversation_reply",
            message=f"{sender.name} replied to your conversation: {conversation.subject}",
            href="/dashboard/inbox",
        )
        # conversation.customer_email is a snapshot taken when the thread
        # was created (see the Conversation model's docstring) -- it's
        # deliberately NOT kept in sync with a later email change, so
        # sending to it here would silently mail a customer's old
        # address if they'd since changed it. Look up the current one.
        recipient = await db.execute(select(User.email).where(User.id == conversation.customer_id))
        notify_email = recipient.scalar_one_or_none()

    await db.commit()
    await db.refresh(conversation)

    if notify_email:
        # Same reasoning as comments.py's equivalent block: sent after
        # commit, wrapped so a delivery failure never surfaces as a
        # failure of the reply that was already saved.
        try:
            await send_conversation_reply_email(notify_email, sender.name, conversation.subject, "/dashboard/inbox")
        except Exception:
            logger.exception("Failed to send conversation-reply notification email to %s", notify_email)

    out = await _load_with_messages(db, [conversation])
    return out[0]


# ---- Quotes -- a lightweight, non-payment-processing offer attached to
# one conversation. Gives a request a trackable, closeable outcome
# (accepted/declined) instead of an open-ended thread with no defined
# end state. Actual payment still happens off-platform; this is just the
# priced offer and the customer's yes/no on it. ----


@router.post("/{conversation_id}/quotes", response_model=ConversationOut)
async def create_quote(
    conversation_id: str,
    payload: QuoteCreateRequest,
    db: AsyncSession = Depends(get_db),
    staff: User = Depends(require_permission("requests:respond")),
):
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")

    quote = ConversationQuote(
        conversation_id=conversation.id,
        created_by_id=staff.id,
        created_by_name=staff.name,
        description=payload.description.strip(),
        # round(), not int(), so e.g. 450000.005 doesn't get silently
        # truncated down a cent by float imprecision.
        amount_cents=round(payload.amount * 100),
        currency=payload.currency.upper(),
    )
    db.add(quote)

    conversation.updated_at = utcnow()
    # Matches add_message's behavior exactly -- sending a quote is just
    # as much a first response to a fresh request as a text reply is,
    # so it should flip 'new' -> 'in_progress' the same way.
    if conversation.status == "new":
        conversation.status = "in_progress"

    await create_notification(
        db,
        user_id=conversation.customer_id,
        type="quote_received",
        message=f"{staff.name} sent you a quote for {conversation.subject}: "
        f"{format_money(quote.amount_cents, quote.currency)}",
        href="/dashboard/inbox",
    )
    recipient = await db.execute(select(User.email).where(User.id == conversation.customer_id))
    notify_email = recipient.scalar_one_or_none()

    await db.commit()
    await db.refresh(conversation)

    if notify_email:
        try:
            await send_quote_email(
                notify_email, staff.name, conversation.subject, quote.amount_cents, quote.currency, "/dashboard/inbox"
            )
        except Exception:
            logger.exception("Failed to send quote notification email to %s", notify_email)

    out = await _load_with_messages(db, [conversation])
    return out[0]


async def _get_quote_in_conversation(db: AsyncSession, conversation_id: str, quote_id: str) -> ConversationQuote:
    result = await db.execute(
        select(ConversationQuote).where(ConversationQuote.id == quote_id, ConversationQuote.conversation_id == conversation_id)
    )
    quote = result.scalar_one_or_none()
    if not quote:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Quote not found")
    return quote


@router.post("/{conversation_id}/quotes/{quote_id}/accept", response_model=ConversationOut)
async def accept_quote(
    conversation_id: str, quote_id: str, db: AsyncSession = Depends(get_db), customer: User = Depends(get_current_customer)
):
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    # Only the customer who owns this conversation can accept its quotes
    # -- not staff, and not some other logged-in customer who happened
    # to guess the id.
    if conversation.customer_id != customer.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized to respond to this quote")

    quote = await _get_quote_in_conversation(db, conversation_id, quote_id)
    if quote.status != "pending":
        raise HTTPException(status.HTTP_409_CONFLICT, f"This quote has already been {quote.status}")

    quote.status = "accepted"
    quote.responded_at = utcnow()
    # The trackable, closeable outcome this feature exists for: accepting
    # a quote closes the request the same way a manual "resolved" would,
    # without staff having to remember to do it themselves.
    conversation.status = "resolved"
    conversation.updated_at = utcnow()
    await db.commit()
    await db.refresh(conversation)

    out = await _load_with_messages(db, [conversation])
    return out[0]


@router.post("/{conversation_id}/quotes/{quote_id}/decline", response_model=ConversationOut)
async def decline_quote(
    conversation_id: str, quote_id: str, db: AsyncSession = Depends(get_db), customer: User = Depends(get_current_customer)
):
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    if conversation.customer_id != customer.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized to respond to this quote")

    quote = await _get_quote_in_conversation(db, conversation_id, quote_id)
    if quote.status != "pending":
        raise HTTPException(status.HTTP_409_CONFLICT, f"This quote has already been {quote.status}")

    quote.status = "declined"
    quote.responded_at = utcnow()
    # Conversation status is deliberately left as-is -- a decline doesn't
    # close the request, since staff may well follow up with a revised
    # quote in the same thread.
    conversation.updated_at = utcnow()
    await db.commit()
    await db.refresh(conversation)

    out = await _load_with_messages(db, [conversation])
    return out[0]


@router.post("/{conversation_id}/quotes/{quote_id}/withdraw", response_model=ConversationOut)
async def withdraw_quote(
    conversation_id: str,
    quote_id: str,
    db: AsyncSession = Depends(get_db),
    staff: User = Depends(require_permission("requests:respond")),
):
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")

    quote = await _get_quote_in_conversation(db, conversation_id, quote_id)
    if quote.status != "pending":
        raise HTTPException(status.HTTP_409_CONFLICT, f"This quote has already been {quote.status}")

    quote.status = "withdrawn"
    quote.responded_at = utcnow()
    conversation.updated_at = utcnow()
    await db.commit()
    await db.refresh(conversation)

    out = await _load_with_messages(db, [conversation])
    return out[0]
