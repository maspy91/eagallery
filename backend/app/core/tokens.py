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


def is_expired(expires_at: datetime, now: datetime | None = None) -> bool:
    """expires_at < now, tolerant of naive datetimes.

    Postgres (production, via asyncpg) always returns tz-aware datetimes
    for a DateTime(timezone=True) column. SQLite (used by the test suite)
    has no native timezone support and silently hands back a naive
    datetime instead, which makes a bare `<` comparison raise
    TypeError: can't compare offset-naive and offset-aware datetimes.
    Treat a naive value as UTC (everything in this app is stored/compared
    in UTC) so the check behaves the same on both backends.
    """
    now = now or utcnow()
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at < now
