# backend/app/schemas/comments.py
# NEW FILE — place at: app/schemas/comments.py

from __future__ import annotations

from pydantic import BaseModel, Field


class CommentCreateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    parent_id: str | None = None


class ModerateCommentRequest(BaseModel):
    flagged: bool


class CommentOut(BaseModel):
    # camelCase to match the frontend's CommentNode type (src/lib/types.ts).
    id: str
    author: str
    authorId: str | None
    text: str
    timestamp: str  # ISO 8601 -- frontend formats it for display
    flagged: bool
    replies: list["CommentOut"] = []


CommentOut.model_rebuild()  # needed for the self-referential `replies: list[CommentOut]`


class AdminCommentOut(CommentOut):
    # Flat (non-nested) shape used only by the admin moderation list, which
    # shows comments across every photo at once rather than one photo's tree.
    photoId: str
    photoTitle: str


class MessageResponse(BaseModel):
    message: str
