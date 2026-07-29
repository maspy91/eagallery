import uuid

import boto3
from botocore.client import Config

from app.core.config import get_settings

settings = get_settings()


def _client():
    """boto3 is sync -- callers from async routes must wrap these in
    starlette.concurrency.run_in_threadpool."""
    return boto3.client(
        "s3",
        endpoint_url=f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def generate_object_key(original_filename: str, prefix: str = "photos") -> str:
    ext = original_filename.rsplit(".", 1)[-1].lower() if "." in original_filename else "bin"
    return f"{prefix}/{uuid.uuid4()}.{ext}"


def generate_presigned_upload_url(object_key: str, content_type: str, expires_in: int = 300) -> str:
    return _client().generate_presigned_url(
        "put_object",
        Params={"Bucket": settings.R2_BUCKET, "Key": object_key, "ContentType": content_type},
        ExpiresIn=expires_in,
    )


def delete_object(object_key: str) -> None:
    _client().delete_object(Bucket=settings.R2_BUCKET, Key=object_key)


def public_url(object_key: str) -> str:
    return f"{settings.R2_PUBLIC_URL.rstrip('/')}/{object_key}"