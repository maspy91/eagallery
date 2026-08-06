# backend/app/schemas/conversations.py
# NEW FILE — place at: app/schemas/conversations.py

from typing import Literal

from pydantic import BaseModel, Field

ConversationStatus = Literal["new", "in_progress", "resolved"]
SenderRole = Literal["customer", "admin", "staff"]


class ConversationCreateRequest(BaseModel):
    subject: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=2000)


class MessageCreateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class ConversationStatusRequest(BaseModel):
    status: ConversationStatus


class ConversationMessageOut(BaseModel):
    # camelCase to match the frontend's ConversationMessage type
    # (src/lib/types.ts).
    id: str
    senderRole: SenderRole
    senderName: str
    text: str
    timestamp: str  # ISO 8601


class ConversationOut(BaseModel):
    # camelCase to match the frontend's BusinessConversation type.
    id: str
    customerId: str
    customerName: str
    customerEmail: str
    subject: str
    status: ConversationStatus
    messages: list[ConversationMessageOut]
    updatedAt: str  # ISO 8601
