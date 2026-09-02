from typing import Literal

from pydantic import BaseModel, Field


class DescribeMediaRequest(BaseModel):
    # objectKey of an ALREADY-UPLOADED photo or video (step 1 of the
    # normal upload flow must have already happened -- this doesn't
    # accept raw file bytes itself, it fetches them back from storage by
    # key, see app/core/storage.py's download_object).
    objectKey: str = Field(min_length=1, max_length=500)
    mediaType: Literal["photo", "video"]
    # Optional free-text hint from the admin ("it's a wireless charger",
    # "focus on the color options") -- folded into the prompt sent to
    # Gemini, not required.
    hint: str = Field(default="", max_length=300)


class DescribeMediaResponse(BaseModel):
    title: str
    description: str
    specs: list[str]


class ChatMessageIn(BaseModel):
    text: str = Field(min_length=1, max_length=1000)
    # Absent on the very first message of a conversation. When present,
    # must reference a thread this customer/session actually owns (see
    # app/routers/ai.py's chat_message for the ownership check) -- lets a
    # returning visitor continue the same thread instead of starting a
    # new one every message.
    threadId: str | None = None


class ChatMessageOut(BaseModel):
    threadId: str
    reply: str
    # True when this message caused the AI to hand the thread off to a
    # human admin (an out-of-scope question, or an explicit custom-project
    # request) -- the frontend uses this to show "connecting you with our
    # team" messaging instead of treating `reply` as an ordinary AI answer.
    handedOffToAdmin: bool
    mode: Literal["ai", "pending_admin", "human"]
