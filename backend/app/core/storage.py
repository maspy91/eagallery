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


def generate_presigned_upload_url(object_key: str, content_type: str = "image/jpeg", expires_in: int = 300) -> str:
    """Creates a pre-signed URL for direct frontend client uploads to Supabase Storage."""
    client = get_supabase_client()
    bucket = settings.SUPABASE_STORAGE_BUCKET

    if not client or not bucket:
        raise RuntimeError("Supabase Storage is not properly configured in environment settings.")

    res = client.storage.from_(bucket).create_signed_upload_url(path=object_key)
    
    # Handle both object and dict response structures from supabase-py
    if isinstance(res, dict):
        return res.get("signed_url") or res.get("signedUrl") or ""
    return getattr(res, "signed_url", getattr(res, "signedUrl", ""))


def delete_object(object_key: str) -> bool:
    """Deletes an object from Supabase Storage using its key or public URL."""
    client = get_supabase_client()
    bucket = settings.SUPABASE_STORAGE_BUCKET

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


def public_url(object_key: str) -> str:
    """Returns the public URL for an object key in Supabase Storage."""
    client = get_supabase_client()
    bucket = settings.SUPABASE_STORAGE_BUCKET

    if not client or not bucket:
        return object_key

    return client.storage.from_(bucket).get_public_url(object_key)