"""
Shared Gemini client wrapper -- both AI features in this app (the
site-scoped live chat and the upload-time description assistant) go
through this module rather than calling google.genai directly, so model
selection, safety settings, and error handling only live in one place.

Uses the SDK's native async client (client.aio.models.generate_content)
since this whole app is async end to end -- there's no reason to run a
sync call in a threadpool when an async one is available.
"""

from __future__ import annotations

import logging

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Explicit rather than relying on the API's own defaults -- this is the
# one place in the app where user-supplied text (a chat message, or an
# uploaded photo/video) is sent to a third-party model, and a public-
# facing chat box is the most likely place someone tries to provoke or
# misuse a model. BLOCK_MEDIUM_AND_ABOVE on every standard category is a
# reasonable, unsurprising default -- not an attempt to be more
# permissive OR more restrictive than Google's own recommendation, just
# explicit about it rather than implicit.
_SAFETY_SETTINGS = [
    types.SafetySetting(category=cat, threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE)
    for cat in (
        types.HarmCategory.HARM_CATEGORY_HARASSMENT,
        types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
    )
]

_client: genai.Client | None = None
_client_checked = False


def is_configured() -> bool:
    return bool(settings.AI_API_KEY)


def _get_client() -> genai.Client | None:
    """Lazily constructed, memoized -- mirrors get_supabase_client()'s
    shape (app/core/storage.py) rather than constructing a fresh client
    per call. Returns None when unconfigured so callers can 404 cleanly,
    same pattern as every other optional integration in this app (Google
    OAuth, Turnstile, Supabase Storage)."""
    global _client, _client_checked
    if not _client_checked:
        _client_checked = True
        if is_configured():
            _client = genai.Client(api_key=settings.AI_API_KEY)
    return _client


class AIUnavailableError(Exception):
    """Raised when the AI feature is called but AI_API_KEY isn't set, or
    the Gemini API itself fails/times out. Routers catch this and return
    a 503, distinct from a 4xx caused by the caller's own request."""


async def generate_text(
    *,
    system_instruction: str,
    contents: list[types.Content] | str,
    max_output_tokens: int | None = None,
) -> str:
    """Text-only generation -- used by the live chat feature. `contents`
    can be a single string (one-shot) or a list of Content objects
    (multi-turn history, oldest first) built by the caller."""
    client = _get_client()
    if client is None:
        raise AIUnavailableError("AI_API_KEY is not configured")

    try:
        response = await client.aio.models.generate_content(
            model=settings.AI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                max_output_tokens=max_output_tokens or settings.AI_MAX_OUTPUT_TOKENS,
                safety_settings=_SAFETY_SETTINGS,
            ),
        )
    except genai_errors.APIError as exc:
        logger.warning("Gemini API error: %s", exc)
        raise AIUnavailableError(str(exc)) from exc

    text = response.text
    if text is None:
        # Most commonly a safety-filter block on either the prompt or the
        # response -- prompt_feedback carries the reason when this
        # happens. Not re-raised as an error: an empty/blocked response
        # is a normal, expected outcome for some inputs, not a failure of
        # the AI feature itself. Callers get "" and decide what to show.
        logger.info("Gemini returned no text (prompt_feedback=%s)", response.prompt_feedback)
        return ""
    return text.strip()


async def generate_media_description(
    *,
    system_instruction: str,
    prompt: str,
    media_bytes: bytes,
    mime_type: str,
) -> str:
    """Multimodal generation for the upload-assist feature -- takes the
    raw bytes of an already-uploaded photo or (short, size-capped) video
    directly, no separate frame-extraction step needed. Gemini's
    multimodal input handles both image and video bytes the same way via
    Part.from_bytes; video support specifically depends on this app's own
    existing 5MB/8s cap keeping clips small enough to send inline rather
    than needing the Files API's resumable upload."""
    client = _get_client()
    if client is None:
        raise AIUnavailableError("AI_API_KEY is not configured")

    try:
        response = await client.aio.models.generate_content(
            model=settings.AI_MODEL,
            contents=[types.Part.from_bytes(data=media_bytes, mime_type=mime_type), types.Part.from_text(text=prompt)],
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                max_output_tokens=settings.AI_MAX_OUTPUT_TOKENS,
                safety_settings=_SAFETY_SETTINGS,
            ),
        )
    except genai_errors.APIError as exc:
        logger.warning("Gemini API error: %s", exc)
        raise AIUnavailableError(str(exc)) from exc

    text = response.text
    if text is None:
        logger.info("Gemini returned no text for media description (prompt_feedback=%s)", response.prompt_feedback)
        return ""
    return text.strip()
