import uuid
from typing import Optional
from supabase import create_client, Client
from app.core.config import get_settings

settings = get_settings()


def get_supabase_client() -> Optional[Client]:
    """Initializes and returns the Supabase client."""
    if settings.SUPABASE_URL and settings.SUPABASE_KEY:
        return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    return None


def generate_object_key(original_filename: str, prefix: str = "photos") -> str:
    """Generates a unique object key (file path) for storage."""
    ext = original_filename.rsplit(".", 1)[-1].lower() if "." in original_filename else "bin"
    return f"{prefix}/{uuid.uuid4()}.{ext}"


def generate_presigned_upload_url(
    object_key: str, content_type: str = "image/jpeg", expires_in: int = 300, bucket: Optional[str] = None
) -> str:
    """Creates a pre-signed URL for direct frontend client uploads to
    Supabase Storage. `bucket` defaults to SUPABASE_STORAGE_BUCKET (the
    photos bucket) for backward compatibility with every existing call
    site -- pass bucket=settings.SUPABASE_VIDEO_BUCKET explicitly for
    video uploads. The actual 10MB/5MB size limits and allowed MIME
    types aren't enforced here (create_signed_upload_url has no
    per-request size parameter) -- they're enforced by Supabase Storage
    itself via each bucket's file_size_limit/allowed_mime_types, set by
    ensure_bucket() below. This function just needs to point at the
    right bucket."""
    client = get_supabase_client()
    bucket = bucket or settings.SUPABASE_STORAGE_BUCKET

    if not client or not bucket:
        raise RuntimeError("Supabase Storage is not properly configured in environment settings.")

    res = client.storage.from_(bucket).create_signed_upload_url(path=object_key)

    # Handle both object and dict response structures from supabase-py
    if isinstance(res, dict):
        return res.get("signed_url") or res.get("signedUrl") or ""
    return getattr(res, "signed_url", getattr(res, "signedUrl", ""))


def delete_object(object_key: str, bucket: Optional[str] = None) -> bool:
    """Deletes an object from Supabase Storage using its key or public URL."""
    client = get_supabase_client()
    bucket = bucket or settings.SUPABASE_STORAGE_BUCKET

    if not client or not bucket or not object_key:
        return False

    # Normalize key if full public URL was passed instead of object key
    path = object_key
    if bucket in object_key:
        path = object_key.split(f"{bucket}/")[-1]

    try:
        client.storage.from_(bucket).remove([path])
        return True
    except Exception:
        return False


def public_url(object_key: str, bucket: Optional[str] = None) -> str:
    """Returns the public URL for an object key in Supabase Storage."""
    client = get_supabase_client()
    bucket = bucket or settings.SUPABASE_STORAGE_BUCKET

    if not client or not bucket:
        return object_key

    return client.storage.from_(bucket).get_public_url(object_key)


def download_object(object_key: str, bucket: Optional[str] = None) -> bytes:
    """Fetches an already-uploaded object's raw bytes back from storage --
    used by the AI upload-assist feature (app/routers/ai.py) to send a
    just-uploaded photo/video to Gemini for a description suggestion,
    without the file ever needing to pass through the browser twice.
    Raises on failure rather than returning empty bytes/None -- unlike
    delete_object's best-effort semantics (where a cleanup failure
    shouldn't block an already-successful delete), a failed download here
    means the AI suggestion genuinely can't be generated, and the caller
    needs to know that to return a clear error instead of silently
    describing zero bytes."""
    client = get_supabase_client()
    bucket = bucket or settings.SUPABASE_STORAGE_BUCKET

    if not client or not bucket:
        raise RuntimeError("Supabase Storage is not properly configured in environment settings.")

    return client.storage.from_(bucket).download(object_key)


def ensure_bucket(bucket: str, *, public: bool, file_size_limit: int, allowed_mime_types: list[str]) -> None:
    """Idempotently creates or updates a Supabase Storage bucket with the
    given size/MIME enforcement. This is where the real 10MB/5MB caps
    actually get enforced -- Supabase Storage itself rejects an
    oversized or wrong-type upload with a real 413/400 at the storage
    service, before the file ever reaches this backend (uploads go
    browser -> Supabase directly via the presigned URL). The app-level
    content_type checks in the routers are defense in depth on top of
    this, not a substitute for it.

    Safe to call on every app startup: if the bucket already exists,
    updates its limits instead of erroring; existing buckets aren't
    silently left with stale/absent limits from before this feature
    existed.
    """
    client = get_supabase_client()
    if not client:
        return

    options = {
        "public": public,
        "file_size_limit": file_size_limit,
        "allowed_mime_types": allowed_mime_types,
    }
    try:
        client.storage.create_bucket(bucket, options=options)
    except Exception:
        # Bucket likely already exists -- update its limits instead.
        # (supabase-py raises on a 409 rather than returning one, and
        # doesn't expose a typed exception for "already exists"
        # specifically, so this stays a broad catch with a real update
        # call behind it rather than silently swallowing a genuine
        # connectivity/auth failure -- update_bucket below will raise
        # its own clear error in that case.)
        client.storage.update_bucket(bucket, options=options)
