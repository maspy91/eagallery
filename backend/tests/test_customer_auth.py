"""
End-to-end customer auth flow, run back to back against an in-memory
sqlite DB + fake Redis (see conftest.py): register -> blocked before
verification -> verify -> session issued -> me -> logout -> me rejected
-> forgot/reset password -> login with the new password.
"""

import pytest


async def test_full_customer_lifecycle(client, captured_emails):
    # 1. Register
    resp = await client.post(
        "/api/customer/register",
        json={"name": "Lena Ortiz", "email": "lena@example.com", "password": "correct-horse-1"},
    )
    assert resp.status_code == 201, resp.text

    # 2. Duplicate registration is rejected
    resp = await client.post(
        "/api/customer/register",
        json={"name": "Lena Ortiz", "email": "lena@example.com", "password": "correct-horse-1"},
    )
    assert resp.status_code == 409

    # 3. Can't log in before verifying
    resp = await client.post(
        "/api/customer/login", json={"email": "lena@example.com", "password": "correct-horse-1"}
    )
    assert resp.status_code == 403
    assert "verify" in resp.json()["detail"].lower()

    # 4. Pull the verification token out of the captured "sent" email
    verify_events = [e for e in captured_emails if e["kind"] == "verify"]
    assert len(verify_events) == 1
    token = verify_events[0]["token"]

    # 5. Verifying logs the user in (sets the session cookie) and returns the user
    resp = await client.post("/api/customer/verify-email", json={"token": token})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["email"] == "lena@example.com"
    assert body["role"] == "customer"
    assert body["emailVerified"] is True
    assert body["avatarInitials"] == "LO"
    assert "customer_session" in resp.cookies

    # 6. Re-using the same verification token fails
    resp = await client.post("/api/customer/verify-email", json={"token": token})
    assert resp.status_code == 400

    # 7. /me reflects the session set by step 5
    resp = await client.get("/api/customer/me")
    assert resp.status_code == 200
    assert resp.json()["email"] == "lena@example.com"

    # 8. Logout clears the session
    resp = await client.post("/api/customer/logout")
    assert resp.status_code == 200
    resp = await client.get("/api/customer/me")
    assert resp.status_code == 401

    # 9. Now login works with the right password...
    resp = await client.post(
        "/api/customer/login", json={"email": "lena@example.com", "password": "correct-horse-1"}
    )
    assert resp.status_code == 200
    assert "customer_session" in resp.cookies

    # 10. ...and /me works again under the new session
    resp = await client.get("/api/customer/me")
    assert resp.status_code == 200

    await client.post("/api/customer/logout")

    # 11. ...and fails with the wrong password
    resp = await client.post(
        "/api/customer/login", json={"email": "lena@example.com", "password": "wrong-password"}
    )
    assert resp.status_code == 401


async def test_forgot_and_reset_password(client, captured_emails):
    await client.post(
        "/api/customer/register",
        json={"name": "Omar Haddad", "email": "omar@example.com", "password": "first-password-1"},
    )
    verify_token = [e for e in captured_emails if e["kind"] == "verify"][0]["token"]
    await client.post("/api/customer/verify-email", json={"token": verify_token})
    await client.post("/api/customer/logout")

    # forgot-password always returns the same generic message, whether or
    # not the account exists -- exercise both cases.
    resp = await client.post("/api/auth/forgot-password", json={"email": "omar@example.com"})
    assert resp.status_code == 200
    generic_message = resp.json()["message"]

    resp = await client.post("/api/auth/forgot-password", json={"email": "nobody@example.com"})
    assert resp.status_code == 200
    assert resp.json()["message"] == generic_message

    reset_token = [e for e in captured_emails if e["kind"] == "reset"][0]["token"]

    # Old password still works until the reset is completed
    resp = await client.post(
        "/api/customer/login", json={"email": "omar@example.com", "password": "first-password-1"}
    )
    assert resp.status_code == 200
    await client.post("/api/customer/logout")

    resp = await client.post(
        "/api/auth/reset-password", json={"token": reset_token, "password": "second-password-2"}
    )
    assert resp.status_code == 200

    # Reset does NOT auto-login
    resp = await client.get("/api/customer/me")
    assert resp.status_code == 401

    # Old password now rejected, new password works
    resp = await client.post(
        "/api/customer/login", json={"email": "omar@example.com", "password": "first-password-1"}
    )
    assert resp.status_code == 401

    resp = await client.post(
        "/api/customer/login", json={"email": "omar@example.com", "password": "second-password-2"}
    )
    assert resp.status_code == 200

    # Reset tokens are single-use
    resp = await client.post(
        "/api/auth/reset-password", json={"token": reset_token, "password": "third-password-3"}
    )
    assert resp.status_code == 400


async def test_rate_limit_on_register(client):
    from app.core.config import get_settings

    settings = get_settings()
    limit = settings.RATE_LIMIT_REGISTER_MAX_ATTEMPTS

    for i in range(limit):
        resp = await client.post(
            "/api/customer/register",
            json={"name": "Spam Bot", "email": f"spam{i}@example.com", "password": "password-123"},
        )
        assert resp.status_code == 201

    resp = await client.post(
        "/api/customer/register",
        json={"name": "Spam Bot", "email": "spam-over-limit@example.com", "password": "password-123"},
    )
    assert resp.status_code == 429
