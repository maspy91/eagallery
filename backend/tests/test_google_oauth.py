"""
Google OAuth ("Sign in with Google") end to end. Google's own endpoints
(token exchange, userinfo) are monkeypatched -- there's no real network
here, and no real Google app to talk to in tests. What's actually
exercised is everything this backend controls: the state-cookie CSRF
check, account creation vs. linking vs. straight login, refusing to
attach to admin/staff accounts, and that the whole thing 404s cleanly
when Google OAuth simply isn't configured.
"""

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.core.security import hash_password
from app.models.user import User
from tests.conftest import TestSessionLocal


async def _create_user(**kwargs) -> User:
    async with TestSessionLocal() as db:
        user = User(**kwargs)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user


@pytest.fixture
def google_oauth_configured(monkeypatch):
    """Settings is an lru_cache()'d singleton -- get_settings() here
    returns the exact same instance the router calls internally, so
    monkeypatching attributes on it affects both, and monkeypatch reverts
    it automatically after the test."""
    from app.core.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setattr(settings, "GOOGLE_REDIRECT_URI", "http://localhost:5173/api/customer/oauth/google/callback")
    return settings


@pytest.fixture
def mock_google_responses(monkeypatch):
    """Patched at the router module level -- customer_auth.py did `from
    app.core.oauth_google import exchange_code_for_tokens,
    fetch_google_userinfo`, which binds its own name (same reasoning as
    every other 'from X import Y' patch elsewhere in this test suite)."""
    import app.routers.customer_auth as customer_auth_module

    userinfo = {"sub": "google-sub-123", "email": "lena@example.com", "name": "Lena Ortiz", "email_verified": True}

    async def _fake_exchange(code: str) -> dict:
        assert code == "valid-code"
        return {"access_token": "fake-access-token"}

    async def _fake_userinfo(access_token: str) -> dict:
        assert access_token == "fake-access-token"
        return dict(userinfo)

    monkeypatch.setattr(customer_auth_module, "exchange_code_for_tokens", _fake_exchange)
    monkeypatch.setattr(customer_auth_module, "fetch_google_userinfo", _fake_userinfo)
    return userinfo


async def test_login_endpoint_redirects_and_sets_state_cookie(client, google_oauth_configured):
    resp = await client.get("/api/customer/oauth/google/login", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert "accounts.google.com" in resp.headers["location"]
    assert "client_id=test-client-id" in resp.headers["location"]
    assert "oauth_state" in resp.cookies


async def test_login_endpoint_404s_when_not_configured(client):
    resp = await client.get("/api/customer/oauth/google/login", follow_redirects=False)
    assert resp.status_code == 404


async def test_callback_rejects_missing_or_mismatched_state(client, google_oauth_configured):
    resp = await client.get(
        "/api/customer/oauth/google/callback", params={"code": "valid-code", "state": "abc"}, follow_redirects=False
    )
    assert resp.status_code in (302, 307)
    assert "error=oauth_failed" in resp.headers["location"]

    client.cookies.set("oauth_state", "cookie-value")
    resp = await client.get(
        "/api/customer/oauth/google/callback",
        params={"code": "valid-code", "state": "different-value"},
        follow_redirects=False,
    )
    assert "error=oauth_failed" in resp.headers["location"]


async def test_new_google_account_created_and_logged_in(client, google_oauth_configured, mock_google_responses):
    client.cookies.set("oauth_state", "matching-state")
    resp = await client.get(
        "/api/customer/oauth/google/callback",
        params={"code": "valid-code", "state": "matching-state"},
        follow_redirects=False,
    )
    assert resp.status_code in (302, 307)
    assert resp.headers["location"].endswith("/dashboard")
    assert "customer_session" in resp.cookies

    resp = await client.get("/api/customer/me")
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "lena@example.com"
    assert body["name"] == "Lena Ortiz"
    assert body["role"] == "customer"
    assert body["emailVerified"] is True


async def test_repeat_login_reuses_same_account_not_duplicated(client, google_oauth_configured, mock_google_responses):
    client.cookies.set("oauth_state", "state-1")
    await client.get(
        "/api/customer/oauth/google/callback", params={"code": "valid-code", "state": "state-1"}, follow_redirects=False
    )
    first_user_id = (await client.get("/api/customer/me")).json()["id"]
    await client.post("/api/customer/logout")

    client.cookies.set("oauth_state", "state-2")
    await client.get(
        "/api/customer/oauth/google/callback", params={"code": "valid-code", "state": "state-2"}, follow_redirects=False
    )
    second_user_id = (await client.get("/api/customer/me")).json()["id"]

    assert first_user_id == second_user_id


async def test_links_to_existing_password_account_by_email(client, google_oauth_configured, mock_google_responses):
    existing = await _create_user(
        email="lena@example.com", name="Lena O.",
        password_hash=hash_password("original-password-1"),
        role="customer", email_verified=False, is_active=True,
    )

    client.cookies.set("oauth_state", "state-1")
    resp = await client.get(
        "/api/customer/oauth/google/callback", params={"code": "valid-code", "state": "state-1"}, follow_redirects=False
    )
    assert resp.status_code in (302, 307)

    resp = await client.get("/api/customer/me")
    assert resp.json()["id"] == existing.id
    assert resp.json()["emailVerified"] is True
    await client.post("/api/customer/logout")

    resp = await client.post(
        "/api/customer/login", json={"email": "lena@example.com", "password": "original-password-1"}
    )
    assert resp.status_code == 200


async def test_never_attaches_to_admin_or_staff_account(client, google_oauth_configured, mock_google_responses):
    await _create_user(
        email="lena@example.com", name="Admin Lena",
        password_hash=hash_password("admin-pass-1"),
        role="admin", email_verified=True, is_active=True,
    )

    client.cookies.set("oauth_state", "state-1")
    resp = await client.get(
        "/api/customer/oauth/google/callback", params={"code": "valid-code", "state": "state-1"}, follow_redirects=False
    )
    assert "error=oauth_failed" in resp.headers["location"]
    assert "customer_session" not in resp.cookies


async def test_deactivated_account_blocked_at_callback(client, google_oauth_configured, mock_google_responses):
    await _create_user(
        email="lena@example.com", name="Lena Ortiz",
        password_hash=hash_password("x"),
        role="customer", email_verified=True, is_active=False,
        google_id="google-sub-123",
    )

    client.cookies.set("oauth_state", "state-1")
    resp = await client.get(
        "/api/customer/oauth/google/callback", params={"code": "valid-code", "state": "state-1"}, follow_redirects=False
    )
    assert "error=account_disabled" in resp.headers["location"]
    assert "customer_session" not in resp.cookies


async def test_unverified_google_email_rejected(client, google_oauth_configured, monkeypatch):
    """Google can return email_verified=false for some federated/enterprise
    identities. The callback must never create an account or link Google
    onto an existing one on the strength of an unverified email -- that's
    the entire safety argument for treating "found by email" as safe to
    auto-link (see the comment in customer_auth.py), so it has to actually
    be checked, not just assumed."""
    import app.routers.customer_auth as customer_auth_module

    async def _fake_exchange(code: str) -> dict:
        return {"access_token": "fake-access-token"}

    async def _fake_userinfo_unverified(access_token: str) -> dict:
        return {
            "sub": "google-sub-unverified",
            "email": "victim@example.com",
            "name": "Attacker Controlled Name",
            "email_verified": False,
        }

    monkeypatch.setattr(customer_auth_module, "exchange_code_for_tokens", _fake_exchange)
    monkeypatch.setattr(customer_auth_module, "fetch_google_userinfo", _fake_userinfo_unverified)

    # Case 1: no existing account with this email -- must not create one.
    client.cookies.set("oauth_state", "state-1")
    resp = await client.get(
        "/api/customer/oauth/google/callback", params={"code": "valid-code", "state": "state-1"}, follow_redirects=False
    )
    assert "error=oauth_failed" in resp.headers["location"]
    assert "customer_session" not in resp.cookies

    async with TestSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == "victim@example.com"))
        assert result.scalar_one_or_none() is None

    # Case 2: an existing password account with this email -- must not get
    # Google silently linked onto it (that would be a new, attacker-known
    # way into someone else's account).
    victim = await _create_user(
        email="victim@example.com", name="Victim",
        password_hash=hash_password("victims-real-password-1"),
        role="customer", email_verified=True, is_active=True,
    )

    client.cookies.set("oauth_state", "state-2")
    resp = await client.get(
        "/api/customer/oauth/google/callback", params={"code": "valid-code", "state": "state-2"}, follow_redirects=False
    )
    assert "error=oauth_failed" in resp.headers["location"]
    assert "customer_session" not in resp.cookies

    async with TestSessionLocal() as db:
        refreshed = await db.get(User, victim.id)
        assert refreshed.google_id is None
