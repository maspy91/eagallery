from typing import Literal

from pydantic import BaseModel, Field

ConversationStatus = Literal["new", "in_progress", "resolved"]
SenderRole = Literal["customer", "admin", "staff"]
QuoteStatus = Literal["pending", "accepted", "declined", "withdrawn"]


class ConversationCreateRequest(BaseModel):
    subject: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=2000)


class MessageCreateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class ConversationStatusRequest(BaseModel):
    status: ConversationStatus


class ConversationMessageOut(BaseModel):
    id: str
    senderRole: SenderRole
    senderName: str
    text: str
    timestamp: str  # ISO 8601


class QuoteCreateRequest(BaseModel):
    description: str = Field(min_length=1, max_length=1000)
    # Whole currency units in the request body (e.g. 450000.00 for
    # ₦450,000), converted to integer cents server-side -- avoids asking
    # the person filling out the form to do that math themselves while
    # still storing/comparing money as an int, not a float.
    amount: float = Field(gt=0, le=1_000_000_000)
    currency: str = Field(default="NGN", min_length=3, max_length=3)


class QuoteOut(BaseModel):
    id: str
    conversationId: str
    createdByName: str
    description: str
    amountCents: int
    currency: str
    status: QuoteStatus
    createdAt: str  # ISO 8601
    respondedAt: str | None  # ISO 8601, null until accepted/declined/withdrawn


class ConversationOut(BaseModel):
    id: str
    customerId: str
    customerName: str
    customerEmail: str
    subject: str
    status: ConversationStatus
    messages: list[ConversationMessageOut]
    quotes: list[QuoteOut]
    updatedAt: str  # ISO 8601


class ConversationStatsOut(BaseModel):
    openCount: int
