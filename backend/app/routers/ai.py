from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core import ai as ai_core
from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import require_permission
from app.core.ip import get_client_ip
from app.core.rate_limit import check_and_increment
from app.core.storage import download_object
from app.models.photo import Photo
from app.models.user import User
from app.models.video import Video
from app.schemas.ai import DescribeMediaRequest, DescribeMediaResponse

router = APIRouter(prefix="/api/ai", tags=["ai"])
settings = get_settings()

DESCRIBE_MAX_MEDIA_BYTES = 5 * 1024 * 1024  # matches MAX_VIDEO_SIZE_BYTES; photos can exceed this (10MB cap) but
# Gemini inline-bytes requests have their own practical payload limits, and
# a gallery description doesn't need to inspect a full-resolution 10MB
# original -- see the docstring on describe_media below.

DESCRIBE_SYSTEM_INSTRUCTION = """You are helping an admin write a product gallery listing for a photography/video \
gallery e-commerce site called EddyArt Gallery. You will be shown one photo or a short video of a product. \
Write a concise, appealing, factual gallery listing for it.

Respond with EXACTLY three sections, each on its own line, in this format and nothing else:
TITLE: <a short, appealing product title, under 8 words>
DESCRIPTION: <1-3 sentences describing the product, its look, and what makes it appealing -- factual, no \
invented specs, no invented brand names, no pricing>
SPECS: <2-5 short comma-separated factual visual observations, e.g. "matte black finish, rounded corners, \
compact size" -- describe only what is visibly true in the image/video, never invent technical specifications \
you cannot see>

Never include markdown formatting, headers, or any text outside these three lines."""


def _parse_describe_response(text: str) -> DescribeMediaResponse:
    """Gemini is instructed to respond in a fixed TITLE:/DESCRIPTION:/
    SPECS: format (see DESCRIBE_SYSTEM_INSTRUCTION) specifically so this
    can be parsed without needing structured/JSON output mode -- keeps the
    prompt simpler and the model's job easier (a plain three-line format
    vs. valid-JSON-with-a-schema). Falls back to putting the whole
    response in `description` if the model doesn't follow the format
    exactly, rather than raising -- an admin still gets something useful
    to edit, instead of a hard error over a formatting slip."""
    title = ""
    description = ""
    specs: list[str] = []

    for line in text.splitlines():
        line = line.strip()
        if line.upper().startswith("TITLE:"):
            title = line.split(":", 1)[1].strip()
        elif line.upper().startswith("DESCRIPTION:"):
            description = line.split(":", 1)[1].strip()
        elif line.upper().startswith("SPECS:"):
            raw = line.split(":", 1)[1].strip()
            specs = [s.strip() for s in raw.split(",") if s.strip()]

    if not title and not description and not specs:
        description = text.strip()

    return DescribeMediaResponse(title=title, description=description, specs=specs[:5])


@router.post(
    "/describe-media",
    response_model=DescribeMediaResponse,
)
async def describe_media(
    payload: DescribeMediaRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("photos:manage")),
):
    """Upload-time description assistance: fetches an already-uploaded
    photo/video back from storage by its objectKey and asks Gemini for a
    suggested title/description/specs. The admin always sees the
    suggestion before it's saved -- this endpoint only returns text, it
    never writes to the Photo/Video row itself, matching how the upload
    forms already work (fill in fields, then a separate PATCH/POST
    saves them).
    """
    if not ai_core.is_configured():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "AI features are not configured")

    ip = get_client_ip(request)
    allowed, retry_after = await check_and_increment(
        f"rl:ai:{ip}", settings.AI_RATE_LIMIT_MAX_REQUESTS, settings.AI_RATE_LIMIT_WINDOW_MINUTES * 60
    )
    if not allowed:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, f"Too many AI requests. Try again in {retry_after}s.")

    # Confirm the objectKey actually belongs to a real Photo/Video row
    # before fetching it from storage -- otherwise this endpoint would
    # accept an arbitrary storage path and burn a Gemini call downloading
    # and describing whatever's there, including objects this feature was
    # never meant to touch.
    if payload.mediaType == "photo":
        result = await db.execute(select(Photo.id).where(Photo.object_key == payload.objectKey))
        bucket = settings.SUPABASE_STORAGE_BUCKET
    else:
        result = await db.execute(select(Video.id).where(Video.object_key == payload.objectKey))
        bucket = settings.SUPABASE_VIDEO_BUCKET

    if result.scalar_one_or_none() is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No matching upload found for that objectKey")

    try:
        media_bytes = await run_in_threadpool(download_object, payload.objectKey, bucket)
    except Exception as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Could not fetch the uploaded file from storage") from exc

    mime_type = "image/jpeg" if payload.mediaType == "photo" else "video/mp4"
    prompt = "Describe this product for the gallery listing."
    if payload.hint:
        prompt += f" Admin's note: {payload.hint}"

    try:
        text = await ai_core.generate_media_description(
            system_instruction=DESCRIBE_SYSTEM_INSTRUCTION,
            prompt=prompt,
            media_bytes=media_bytes,
            mime_type=mime_type,
        )
    except ai_core.AIUnavailableError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "AI description is temporarily unavailable") from exc

    if not text:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Could not generate a description for this file"
        )

    return _parse_describe_response(text)
