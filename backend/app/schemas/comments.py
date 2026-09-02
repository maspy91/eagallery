from __future__ import annotations

from pydantic import BaseModel, Field


class CommentCreateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    parent_id: str | None = None


class ModerateCommentRequest(BaseModel):
    flagged: bool


class CommentOut(BaseModel):
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
    # shows comments across every photo/video at once rather than one
    # item's tree. Exactly one of photoId/videoId is set (mirrors the
    # Comment.photo_id/video_id exactly-one-set DB constraint) -- the
    # frontend uses whichever is present to decide the comment's link
    # target and label ("Photo" vs "Video").
    photoId: str | None = None
    photoTitle: str | None = None
    videoId: str | None = None
    videoTitle: str | None = None


class MessageResponse(BaseModel):
    message: str
