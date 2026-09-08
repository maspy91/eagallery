"""
End-to-end admin/staff auth flow: bootstrap an admin directly in the test
DB (mirrors what ensure_admin_bootstrap() does from ADMIN_EMAIL/
ADMIN_PASSWORD at real startup) -> admin login -> invite staff -> staff
accepts invite -> staff login -> permission boundary -> revoke -> revoked
staff can no longer log in. Also checks the customer/admin login systems
never cross-validate each other's credentials.
"""

import pytest_asyncio

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


@pytest_asyncio.fixture
async def admin_user():
    return await _create_user(
        email="admin@eddyartgallery.app",
        name="Admin",
        password_hash=hash_password("super-secret-admin-1"),
        role="admin",
        email_verified=True,
        is_active=True,
    )


async def test_admin_login_and_me(client, admin_user):
    resp = await client.post(
        "/api/auth/login", json={"email": "admin@eddyartgallery.app", "password": "super-secret-admin-1"}
    )
    assert resp.status_code == 200, resp.text
    assert "admin_session" in resp.cookies

    resp = await client.get("/api/auth/me")
    assert resp.status_code == 200
    assert resp.json()["role"] == "admin"


async def test_customer_and_admin_logins_never_cross(client, admin_user):
    # Registered as customer, verified.
    await client.post(
        "/api/customer/register",
        json={"name": "Priya Nair", "email": "priya@example.com", "password": "customer-pass-1"},
    )
    async with TestSessionLocal() as db:
        from sqlalchemy import select

        result = await db.execute(select(User).where(User.email == "priya@example.com"))
        customer = result.scalar_one()
        customer.email_verified = True
        await db.commit()

    # A customer's credentials are rejected on the admin login endpoint...
    resp = await client.post(
        "/api/auth/login", json={"email": "priya@example.com", "password": "customer-pass-1"}
    )
    assert resp.status_code == 401

    # ...and the admin's credentials are rejected on the customer login endpoint.
    resp = await client.post(
        "/api/customer/login",
        json={"email": "admin@eddyartgallery.app", "password": "super-secret-admin-1"},
    )
    assert resp.status_code == 401


async def test_staff_invite_accept_and_permission_boundary(client, admin_user, captured_emails):
    # Not logged in yet -- invite is rejected.
    resp = await client.post("/api/auth/staff/invite", json={"name": "Jordan Blake", "email": "jordan@example.com"})
    assert resp.status_code == 401

    await client.post(
        "/api/auth/login", json={"email": "admin@eddyartgallery.app", "password": "super-secret-admin-1"}
    )

    resp = await client.post("/api/auth/staff/invite", json={"name": "Jordan Blake", "email": "jordan@example.com"})
    assert resp.status_code == 200, resp.text

    invite_token = [e for e in captured_emails if e["kind"] == "invite"][0]["token"]

    # Admin session is separate from whatever session accept-invite creates
    # -- log out of the admin session first to make that boundary explicit.
    await client.post("/api/auth/logout")

    resp = await client.post(
        "/api/auth/staff/accept-invite", json={"token": invite_token, "password": "jordan-pass-1"}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["role"] == "staff"
    assert body["email"] == "jordan@example.com"
    assert "admin_session" in resp.cookies

    # Staff is logged in now (from accept-invite) -- confirm, then log out
    # and log back in explicitly through the normal login endpoint too.
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 200
    assert resp.json()["role"] == "staff"

    # Staff lacks roles:manage -- listing/inviting/revoking staff is forbidden.
    resp = await client.get("/api/auth/staff")
    assert resp.status_code == 403

    resp = await client.post(
        "/api/auth/staff/invite", json={"name": "Someone Else", "email": "someone@example.com"}
    )
    assert resp.status_code == 403

    await client.post("/api/auth/logout")

    # Staff can log in normally through the regular login endpoint too.
    resp = await client.post("/api/auth/login", json={"email": "jordan@example.com", "password": "jordan-pass-1"})
    assert resp.status_code == 200
    await client.post("/api/auth/logout")

    # Invite tokens are single-use.
    resp = await client.post(
        "/api/auth/staff/accept-invite", json={"token": invite_token, "password": "another-pass-1"}
    )
    assert resp.status_code == 400


async def test_admin_can_list_and_revoke_staff(client, admin_user, captured_emails):
    await client.post(
        "/api/auth/login", json={"email": "admin@eddyartgallery.app", "password": "super-secret-admin-1"}
    )
    await client.post("/api/auth/staff/invite", json={"name": "Sarah Chen", "email": "sarah@example.com"})
    invite_token = [e for e in captured_emails if e["kind"] == "invite"][0]["token"]

    await client.post("/api/auth/logout")
    resp = await client.post(
        "/api/auth/staff/accept-invite", json={"token": invite_token, "password": "sarah-pass-1"}
    )
    staff_id = resp.json()["id"]
    await client.post("/api/auth/logout")

    # Back in as admin.
    await client.post(
        "/api/auth/login", json={"email": "admin@eddyartgallery.app", "password": "super-secret-admin-1"}
    )

    resp = await client.get("/api/auth/staff")
    assert resp.status_code == 200
    assert any(s["id"] == staff_id for s in resp.json())

    resp = await client.delete(f"/api/auth/staff/{staff_id}")
    assert resp.status_code == 200

    await client.post("/api/auth/logout")

    # Revoked staff account no longer exists -- login now fails.
    resp = await client.post("/api/auth/login", json={"email": "sarah@example.com", "password": "sarah-pass-1"})
    assert resp.status_code == 401


async def test_rate_limit_on_admin_login(client, admin_user):
    from app.core.config import get_settings

    settings = get_settings()
    limit = settings.RATE_LIMIT_LOGIN_MAX_ATTEMPTS

    for _ in range(limit):
        resp = await client.post(
            "/api/auth/login", json={"email": "admin@eddyartgallery.app", "password": "wrong-password"}
        )
        assert resp.status_code == 401

    resp = await client.post(
        "/api/auth/login", json={"email": "admin@eddyartgallery.app", "password": "wrong-password"}
    )
    assert resp.status_code == 429


# ============================================================
# Account/profile settings: update name, change email, change password
# ============================================================


async def _login_admin(client, email="admin@eddyartgallery.app", password="super-secret-admin-1"):
    resp = await client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()


async def test_admin_update_profile_name_only(client, admin_user):
    await _login_admin(client)

    resp = await client.patch("/api/auth/me", json={"name": "Admin Updated"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["name"] == "Admin Updated"
    assert resp.json()["email"] == "admin@eddyartgallery.app"

    resp = await client.get("/api/auth/me")
    assert resp.json()["name"] == "Admin Updated"


async def test_admin_update_profile_requires_login(client):
    resp = await client.patch("/api/auth/me", json={"name": "Nobody"})
    assert resp.status_code == 401


async def test_admin_change_email_requires_correct_current_password(client, admin_user):
    await _login_admin(client)

    resp = await client.post(
        "/api/auth/change-email", json={"email": "new-admin@example.com", "currentPassword": "wrong-password"}
    )
    assert resp.status_code == 401

    resp = await client.get("/api/auth/me")
    assert resp.json()["email"] == "admin@eddyartgallery.app"


async def test_admin_change_email_success_and_rejects_duplicate(client, admin_user):
    other_staff = await _create_user(
        email="other-staff@example.com",
        name="Other Staff",
        password_hash=hash_password("other-pass-1"),
        role="staff",
        email_verified=True,
        is_active=True,
    )

    await _login_admin(client)

    # Can't take an email already registered to another account (the
    # unique constraint is global across roles, not just admin/staff).
    resp = await client.post(
        "/api/auth/change-email",
        json={"email": "other-staff@example.com", "currentPassword": "super-secret-admin-1"},
    )
    assert resp.status_code == 409

    # A genuinely new email succeeds immediately -- unlike the customer
    # side, admin/staff login never checks email_verified, so there's no
    # re-verification step and no session disruption.
    resp = await client.post(
        "/api/auth/change-email",
        json={"email": "admin-new@example.com", "currentPassword": "super-secret-admin-1"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["email"] == "admin-new@example.com"

    resp = await client.get("/api/auth/me")
    assert resp.status_code == 200
    assert resp.json()["email"] == "admin-new@example.com"

    # Old email no longer works for login; new one does.
    await client.post("/api/auth/logout")
    resp = await client.post(
        "/api/auth/login", json={"email": "admin@eddyartgallery.app", "password": "super-secret-admin-1"}
    )
    assert resp.status_code == 401
    resp = await client.post(
        "/api/auth/login", json={"email": "admin-new@example.com", "password": "super-secret-admin-1"}
    )
    assert resp.status_code == 200


async def test_admin_change_password_success_and_wrong_current_password(client, admin_user):
    await _login_admin(client)

    resp = await client.post(
        "/api/auth/change-password", json={"currentPassword": "wrong-one", "newPassword": "brand-new-admin-1"}
    )
    assert resp.status_code == 401

    resp = await client.post(
        "/api/auth/change-password",
        json={"currentPassword": "super-secret-admin-1", "newPassword": "brand-new-admin-1"},
    )
    assert resp.status_code == 200, resp.text

    # Current session survives a password change.
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 200

    await client.post("/api/auth/logout")
    resp = await client.post(
        "/api/auth/login", json={"email": "admin@eddyartgallery.app", "password": "super-secret-admin-1"}
    )
    assert resp.status_code == 401
    resp = await client.post(
        "/api/auth/login", json={"email": "admin@eddyartgallery.app", "password": "brand-new-admin-1"}
    )
    assert resp.status_code == 200


async def test_staff_can_also_manage_own_profile(client, admin_user, captured_emails):
    # Staff accounts share the exact same endpoints as admin -- create one
    # via the real invite/accept flow (not _create_user directly) so this
    # also proves the endpoints work for a staff-created session, not just
    # one seeded straight into the DB.
    await _login_admin(client)
    resp = await client.post("/api/auth/staff/invite", json={"name": "Sarah K", "email": "sarah@example.com"})
    assert resp.status_code == 200, resp.text
    invite_token = [e for e in captured_emails if e["kind"] == "invite"][0]["token"]
    await client.post("/api/auth/logout")

    resp = await client.post(
        "/api/auth/staff/accept-invite", json={"token": invite_token, "password": "sarah-pass-1"}
    )
    assert resp.status_code == 200, resp.text

    resp = await client.patch("/api/auth/me", json={"name": "Sarah Kim"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["role"] == "staff"
    assert resp.json()["name"] == "Sarah Kim"

    resp = await client.post(
        "/api/auth/change-password", json={"currentPassword": "sarah-pass-1", "newPassword": "sarah-pass-2-new"}
    )
    assert resp.status_code == 200, resp.text
