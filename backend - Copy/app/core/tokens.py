import hashlib
import secrets
from datetime import datetime, timedelta, timezone


def generate_raw_token() -> str:
    """256 bits of randomness, URL-safe -- this is what gets emailed and
    put in the link. Never stored anywhere, including logs."""
    return secrets.token_urlsafe(32)


def hash_token(raw_token: str) -> str:
    """What actually gets stored/queried. SHA-256 is fine here (not a
    password hash) -- the input already has 256 bits of entropy, so
    there's nothing for an attacker to brute-force even with a fast hash."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def expiry_from_now(**kwargs) -> datetime:
    """expiry_from_now(hours=24) / expiry_from_now(minutes=30)"""
    return datetime.now(timezone.utc) + timedelta(**kwargs)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
