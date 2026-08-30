import os

# Settings requires these at import time -- set safe test values before
# app.core.config (and anything importing it) is ever imported. Real
# per-environment values come from .env / Render env vars outside tests.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:password@localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
# 32+ bytes to avoid PyJWT's InsecureKeyLengthWarning on every token
# encode/decode in the test run (HS256 wants >= 32 bytes; the old
# 31-byte value was under that).
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only-32b")
os.environ.setdefault("DEBUG", "True")
os.environ.setdefault("TURNSTILE_ENABLED", "False")
# Settings.FRONTEND_URL has no default (required in every real
# environment -- see app/core/config.py) so it must be set here too, or
# Settings() raises ValidationError before a single test can even be
# collected.
os.environ.setdefault("FRONTEND_URL", "http://localhost:5173")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core import rate_limit as rate_limit_module
from app.core import redis as redis_module
from app.core.database import Base, get_db
from app.main import app
from tests.fakes import FakeRedis

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)


async def _override_get_db():
    async with TestSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch):
    """Rate limiting is Redis-backed; swap in an in-memory fake so tests
    don't need a real (network-reachable) Redis instance. Patched on both
    modules since rate_limit.py did `from app.core.redis import
    redis_client`, which binds its own name -- patching app.core.redis
    alone wouldn't affect the reference rate_limit.py already holds."""
    fake = FakeRedis()
    monkeypatch.setattr(rate_limit_module, "redis_client", fake)
    monkeypatch.setattr(redis_module, "redis_client", fake)
    return fake


@pytest_asyncio.fixture(autouse=True)
async def _setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def captured_emails(monkeypatch):
    """Email sending is monkeypatched at the router level (each router did
    `from app.core.email import send_x`, which binds its own name -- same
    reasoning as the redis_client patch above) so tests can grab the raw
    token that would have been emailed, without a real mailbox."""
    import app.routers.admin_auth as admin_auth_module
    import app.routers.customer_auth as customer_auth_module

    sent: list[dict] = []

    async def _fake_verification(to_email: str, token: str) -> bool:
        sent.append({"kind": "verify", "to": to_email, "token": token})
        return True

    async def _fake_reset(to_email: str, token: str) -> bool:
        sent.append({"kind": "reset", "to": to_email, "token": token})
        return True

    async def _fake_invite(to_email: str, token: str) -> bool:
        sent.append({"kind": "invite", "to": to_email, "token": token})
        return True

    monkeypatch.setattr(customer_auth_module, "send_verification_email", _fake_verification)
    monkeypatch.setattr(admin_auth_module, "send_password_reset_email", _fake_reset)
    monkeypatch.setattr(admin_auth_module, "send_staff_invite_email", _fake_invite)

    return sent
