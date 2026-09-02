from typing import Literal

from pydantic import BaseModel, Field

VideoStatus = Literal["draft", "published", "flagged"]


class VideoUploadUrlRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=100)
    # Checked against settings.MAX_VIDEO_SIZE_BYTES before a presigned URL
    # is even issued (see the video upload endpoint) -- this is a fast,
    # honest-client check, NOT the real enforcement boundary. The actual
    # boundary is the videos bucket's file_size_limit (see
    # app/core/storage.py's ensure_bucket()), enforced by Supabase
    # Storage itself on the direct browser upload that follows, which the
    # backend never sees the bytes of and so can't verify server-side any
    # other way.
    size_bytes: int = Field(gt=0)
    # Same reasoning as size_bytes: checked here for a fast rejection with
    # a clear error message, but duration can't be enforced by the
    # storage service the way size/MIME can -- so VideoCreateRequest
    # below checks it again, against the CLIENT-reported duration of the
    # file that actually finished uploading, not this pre-upload claim.
    duration_seconds: float = Field(gt=0)


class VideoUploadUrlResponse(BaseModel):
    objectKey: str
    uploadUrl: str
    publicUrl: str


class VideoCreateRequest(BaseModel):
    objectKey: str = Field(min_length=1, max_length=500)
    posterObjectKey: str | None = Field(default=None, max_length=500)
    title: str = Field(min_length=1, max_length=200)
    category: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=2000)
    specs: list[str] = Field(default_factory=list, max_length=20)
    durationSeconds: float = Field(gt=0)
    mimeType: str = Field(min_length=1, max_length=100)


class VideoUpdateRequest(BaseModel):
    # All optional -- PATCH semantics, only supplied fields change.
    title: str | None = Field(default=None, min_length=1, max_length=200)
    category: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    specs: list[str] | None = Field(default=None, max_length=20)
    status: VideoStatus | None = None
    posterObjectKey: str | None = Field(default=None, max_length=500)


class VideoOut(BaseModel):
    # camelCase to match the frontend convention (see PhotoOut).
    id: str
    video: str  # public URL of the video file itself
    objectKey: str  # same reasoning as PhotoOut.objectKey -- not sensitive, avoids URL-parsing on the frontend
    poster: str | None  # public URL of the poster image, or None if not set
    title: str
    category: str
    viewCount: int
    likeCount: int
    description: str
    specs: list[str]
    status: VideoStatus
    durationSeconds: float
    liked: bool  # only meaningful when the request is from a logged-in customer; False otherwise


class LikeResponse(BaseModel):
    liked: bool
    likeCount: int


class MessageResponse(BaseModel):
    message: str
