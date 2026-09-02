import uuid

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, String, Text, func

from app.core.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class ChatThread(Base):
    """
    One conversation with the site's AI/live chat widget -- distinct
    from Conversation (Business Requests), which is a different feature
    (a longer-form, always-human, always-logged-in-customer inquiry
    system). ChatThread is deliberately lighter-weight and works for
    anonymous visitors too, matching how real chat widgets behave (no
    signup wall for a first "hi, do you sell X?" message).

    Identity: EXACTLY ONE of customer_id / guest_token is set (enforced
    by the check constraint below), mirroring the photo_id/video_id
    exactly-one pattern already used on Comment. A logged-in customer's
    threads are tied to their real account (customer_id); an anonymous
    visitor is identified only by an opaque guest_token stored in a
    cookie (see app/core/chat_session.py) -- there is no way to look up
    an anonymous visitor's thread without that same cookie, by design.

    mode is the live state machine driving everything: 'ai' (the AI
    responds automatically), 'pending_admin' (the AI has forwarded this
    thread -- an out-of-scope question, or a custom-project request --
    and it's waiting in the admin queue), 'human' (an admin has picked
    it up; the AI stays silent). Transitions in both directions --
    ai -> pending_admin (AI forwards), pending_admin -> human (admin
    picks up), human -> ai (admin explicitly hands back, full history
    retained so the AI resumes informed rather than cold) -- see
    app/routers/chat.py for exactly where each transition happens.

    contact_email is asked for specifically at the point of handoff (see
    the router) -- not required to chat at all, only required before the
    AI forwards to a human, since a human follow-up on, say, a custom
    project request is useless with no way to reach the person back.
    """

    __tablename__ = "chat_threads"
    __table_args__ = (
        CheckConstraint(
            "(customer_id IS NOT NULL AND guest_token IS NULL) OR (customer_id IS NULL AND guest_token IS NOT NULL)",
            name="ck_chat_threads_exactly_one_identity",
        ),
    )

    id = Column(String(36), primary_key=True, default=gen_uuid)
    customer_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    guest_token = Column(String(64), nullable=True, index=True)

    mode = Column(String(20), nullable=False, default="ai", index=True)  # ai | pending_admin | human
    contact_email = Column(String(255), nullable=True)

    # Snapshot, same reasoning as Comment.author_name / Conversation's
    # customer_name -- a display name for the admin queue/thread view
    # that doesn't require a join and doesn't rewrite history if the
    # customer later changes their name. "Guest" for anonymous visitors
    # who haven't given a name (contact_email capture doesn't ask for
    # one; kept simple).
    display_name = Column(String(100), nullable=False, default="Guest")

    # Which admin/staff user currently owns this thread once it's in
    # 'human' mode -- nullable (unset while mode is 'ai'/'pending_admin').
    # Not strictly required for a single-admin deployment, but matters
    # the moment there's more than one admin/staff account: without this,
    # two staff members could both reply to the same customer at once
    # with no way to tell who's already handling it.
    assigned_admin_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ChatMessage(Base):
    """
    sender_role distinguishes who actually said this -- 'ai', 'customer'
    (used for both logged-in and anonymous senders; ChatThread already
    captures which one this thread belongs to), or 'admin'. Kept as its
    own value (not reusing Conversation's customer/admin/staff roles)
    because 'ai' has to be representable here and isn't a real sender
    role anywhere else in the app.

    Full history is retained across every mode transition -- when a
    thread moves human -> ai, the AI is given this entire list (including
    the admin's own messages) as its context on the next call, per the
    explicit design decision that a handback should resume informed, not
    cold. See app/routers/chat.py's _build_gemini_history.
    """

    __tablename__ = "chat_messages"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    thread_id = Column(String(36), ForeignKey("chat_threads.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_role = Column(String(20), nullable=False)  # ai | customer | admin
    sender_name = Column(String(100), nullable=False)
    sender_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    text = Column(Text, nullable=False)

    # True for the one system-style message marking a mode transition
    # (e.g. "Connected you with our team" / "An admin has joined the
    # chat" / "Resuming with our assistant") -- rendered differently by
    # the frontend (centered, muted) rather than as a normal chat bubble,
    # and excluded from the history handed back to Gemini on a handback
    # (it's UI narration, not part of the actual conversation content).
    is_system = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
