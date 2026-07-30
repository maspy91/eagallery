from datetime import datetime, timedelta, timezone

import jwt as pyjwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError

from app.core.config import get_settings

# Argon2id via argon2-cffi directly (not passlib -- passlib is unmaintained
# since 2020 with known breaks against recent argon2-cffi/bcrypt versions).
# Argon2id is the current OWASP-recommended default for new systems.
_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return _hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, InvalidHashError, ValueError):
        return False


def create_access_token(subject: str, role: str, expires_delta: timedelta | None = None) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    to_encode = {
        "sub": subject,
        "role": role,
        "iat": now,
        "exp": now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)),
    }
    return pyjwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Algorithm is pinned to settings.ALGORITHM on decode, never read from
    the token's own header -- that pin is what prevents algorithm-confusion
    attacks, independent of which JWT library is used."""
    settings = get_settings()
    return pyjwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])