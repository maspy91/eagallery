from typing import Literal

from pydantic import BaseModel, Field

PhotoStatus = Literal["draft", "published", "flagged"]


class UploadUrlRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=100)


class UploadUrlResponse(BaseModel):
    objectKey: str
    uploadUrl: str
    publicUrl: str


class PhotoCreateRequest(BaseModel):
    objectKey: str = Field(min_length=1, max_length=500)
    title: str = Field(min_length=1, max_length=200)
    category: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=2000)
    specs: list[str] = Field(default_factory=list, max_length=20)


class PhotoUpdateRequest(BaseModel):
    # All optional -- PATCH semantics, only supplied fields change.
    title: str | None = Field(default=None, min_length=1, max_length=200)
    category: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    specs: list[str] | None = Field(default=None, max_length=20)
    status: PhotoStatus | None = None


class PhotoOut(BaseModel):
    # camelCase to match the frontend's GalleryItem type (src/lib/types.ts).
    id: str
    image: str
    # Not sensitive -- Supabase's public URL format already embeds this as
    # its trailing path segments, so `image` leaks it either way. Exposed
    # as its own field so callers (specifically the admin "Suggest
    # description" AI feature, which needs to hand this back to
    # POST /api/ai/describe-media) don't have to parse it back out of a
    # URL string, which would silently break if the URL format ever
    # changed.
    objectKey: str
    title: str
    category: str
    viewCount: int
    likeCount: int
    description: str
    specs: list[str]
    status: PhotoStatus
    liked: bool  # only meaningful when the request is from a logged-in customer; False otherwise


class LikeResponse(BaseModel):
    liked: bool
    likeCount: int


class MessageResponse(BaseModel):
    message: str
