from typing import Literal

from pydantic import BaseModel, Field

ChatMode = Literal["ai", "pending_admin", "human"]
ChatSenderRole = Literal["ai", "customer", "admin"]


class ChatMessageIn(BaseModel):
    text: str = Field(min_length=1, max_length=1000)
    # Present from the 2nd message onward in a thread; absent on the
    # very first message, which creates a new thread. The endpoint
    # verifies this thread actually belongs to the caller (their
    # customer_id, or their guest_token cookie) -- see chat.py's
    # send_message.
    threadId: str | None = None


class ChatMessageOut(BaseModel):
    id: str
    senderRole: ChatSenderRole
    senderName: str
    text: str
    timestamp: str
    isSystem: bool


class ChatThreadOut(BaseModel):
    id: str
    mode: ChatMode
    contactEmail: str | None
    messages: list[ChatMessageOut]


class ChatReplyOut(BaseModel):
    threadId: str
    # The AI's reply text, or "" when mode is pending_admin/human (no AI
    # response was generated -- the customer's message was still saved
    # and, if this call is what triggered the handoff, a system message
    # was added explaining that). The frontend shows the full updated
    # `messages` list regardless, so this is really just a convenience
    # for "did the AI say something new just now".
    reply: str
    mode: ChatMode
    messages: list[ChatMessageOut]


class ContactEmailIn(BaseModel):
    email: str = Field(min_length=3, max_length=255)


# ---- Admin side ----


class AdminChatThreadOut(BaseModel):
    id: str
    mode: ChatMode
    displayName: str
    contactEmail: str | None
    isGuest: bool
    assignedAdminName: str | None
    lastMessagePreview: str
    updatedAt: str


class AdminChatThreadDetailOut(BaseModel):
    id: str
    mode: ChatMode
    displayName: str
    contactEmail: str | None
    isGuest: bool
    messages: list[ChatMessageOut]


class AdminChatReplyIn(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class AdminChatModeIn(BaseModel):
    mode: Literal["human", "ai"]  # admin can only ever pick up (-> human) or hand back (-> ai);
    # pending_admin is only ever set by the AI's own forward action, never chosen by an admin directly.
