"""
Admin customer management: list/search/filter, the /stats count, and the
activate/deactivate action -- plus permission boundaries (customer can't
reach any of it, and staff specifically can't either, since
customers:manage is admin-only, unlike most other admin capabilities in
this app).
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
        email="admin@eddyartgallery.app", name="Admin",
        password_hash=hash_password("super-secret-admin-1"),
        role="admin", email_verified=True, is_active=True,
    )


@pytest_asyncio.fixture
async def staff_user():
    return await _create_user(
        email="staffer@example.com", name="Staffer",
        password_hash=hash_password("staff-pass-1"),
        role="staff", email_verified=True, is_active=True,
    )


@pytest_asyncio.fixture
async def customer_user():
    return await _create_user(
        email="lena@example.com", name="Lena Ortiz",
        password_hash=hash_password("customer-pass-1"),
        role="customer", email_verified=True, is_active=True,
    )


async def _login_admin(client, admin_user):
    resp = await client.post("/api/auth/login", json={"email": "admin@eddyartgallery.app", "password": "super-secret-admin-1"})
    assert resp.status_code == 200, resp.text


async def _login_staff(client, staff_user):
    resp = await client.post("/api/auth/login", json={"email": "staffer@example.com", "password": "staff-pass-1"})
    assert resp.status_code == 200, resp.text


async def _login_customer(client, customer_user):
    resp = await client.post("/api/customer/login", json={"email": "lena@example.com", "password": "customer-pass-1"})
    assert resp.status_code == 200, resp.text


async def test_list_customers_excludes_staff_and_admin(client, admin_user, staff_user, customer_user):
    await _login_admin(client, admin_user)

    resp = await client.get("/api/customers")
    assert resp.status_code == 200, resp.text
    emails = [c["email"] for c in resp.json()]
    assert "lena@example.com" in emails
    assert "admin@eddyartgallery.app" not in emails
    assert "staffer@example.com" not in emails


async def test_search_matches_name_or_email_case_insensitively(client, admin_user):
    await _create_user(
        email="priya.nair@example.com", name="Priya Nair",
        password_hash=hash_password("x"), role="customer", email_verified=True, is_active=True,
    )
    await _create_user(
        email="omar@example.com", name="Omar Haddad",
        password_hash=hash_password("x"), role="customer", email_verified=True, is_active=True,
    )
    await _login_admin(client, admin_user)

    # Matches by name, case-insensitively.
    resp = await client.get("/api/customers", params={"q": "PRIYA"})
    assert resp.status_code == 200, resp.text
    names = [c["name"] for c in resp.json()]
    assert names == ["Priya Nair"]

    # Matches by (partial) email too.
    resp = await client.get("/api/customers", params={"q": "omar@"})
    assert resp.status_code == 200, resp.text
    assert [c["name"] for c in resp.json()] == ["Omar Haddad"]

    # No match.
    resp = await client.get("/api/customers", params={"q": "nobody-like-this"})
    assert resp.status_code == 200, resp.text
    assert resp.json() == []


async def test_filter_by_active_status(client, admin_user, customer_user):
    deactivated = await _create_user(
        email="banned@example.com", name="Banned User",
        password_hash=hash_password("x"), role="customer", email_verified=True, is_active=False,
    )
    await _login_admin(client, admin_user)

    resp = await client.get("/api/customers", params={"is_active": "true"})
    assert resp.status_code == 200, resp.text
    emails = {c["email"] for c in resp.json()}
    assert "lena@example.com" in emails
    assert "banned@example.com" not in emails

    resp = await client.get("/api/customers", params={"is_active": "false"})
    assert resp.status_code == 200, resp.text
    emails = {c["email"] for c in resp.json()}
    assert "banned@example.com" in emails
    assert "lena@example.com" not in emails


async def test_customer_stats_count(client, admin_user, customer_user):
    await _create_user(
        email="second@example.com", name="Second Customer",
        password_hash=hash_password("x"), role="customer", email_verified=True, is_active=True,
    )
    await _login_admin(client, admin_user)

    resp = await client.get("/api/customers/stats")
    assert resp.status_code == 200, resp.text
    assert resp.json()["totalCount"] == 2


async def test_deactivate_and_reactivate_customer(client, admin_user, customer_user):
    await _login_admin(client, admin_user)

    resp = await client.patch(f"/api/customers/{customer_user.id}", json={"isActive": False})
    assert resp.status_code == 200, resp.text
    assert resp.json()["isActive"] is False

    # A deactivated customer can no longer log in -- confirms this
    # endpoint's is_active flag is the same one login() actually checks
    # (backend/app/routers/customer_auth.py's login rejects with 403 when
    # is_active is False), not a cosmetic flag that does nothing.
    resp = await client.post("/api/customer/login", json={"email": "lena@example.com", "password": "customer-pass-1"})
    assert resp.status_code == 403

    resp = await client.patch(f"/api/customers/{customer_user.id}", json={"isActive": True})
    assert resp.status_code == 200, resp.text
    assert resp.json()["isActive"] is True

    resp = await client.post("/api/customer/login", json={"email": "lena@example.com", "password": "customer-pass-1"})
    assert resp.status_code == 200


async def test_cannot_target_a_staff_or_admin_row_through_this_endpoint(client, admin_user, staff_user):
    """The endpoint filters on role == 'customer', so it should be
    impossible to (de)activate a staff or admin account through it, even
    if you know their user id."""
    await _login_admin(client, admin_user)

    resp = await client.patch(f"/api/customers/{staff_user.id}", json={"isActive": False})
    assert resp.status_code == 404

    resp = await client.patch(f"/api/customers/{admin_user.id}", json={"isActive": False})
    assert resp.status_code == 404


async def test_unknown_customer_id_returns_404(client, admin_user):
    await _login_admin(client, admin_user)
    resp = await client.patch("/api/customers/does-not-exist", json={"isActive": False})
    assert resp.status_code == 404


async def test_staff_cannot_access_customer_management(client, staff_user, customer_user):
    """customers:manage is admin-only, unlike most other admin
    capabilities in this app (photos:manage, comments:moderate,
    requests:respond, analytics:view all include staff)."""
    await _login_staff(client, staff_user)

    resp = await client.get("/api/customers")
    assert resp.status_code == 403

    resp = await client.get("/api/customers/stats")
    assert resp.status_code == 403

    resp = await client.patch(f"/api/customers/{customer_user.id}", json={"isActive": False})
    assert resp.status_code == 403


async def test_customer_cannot_access_customer_management(client, customer_user):
    await _login_customer(client, customer_user)

    resp = await client.get("/api/customers")
    assert resp.status_code == 401

    resp = await client.get("/api/customers/stats")
    assert resp.status_code == 401


# ============================================================
# Date-range filtering and CSV export
# ============================================================


async def test_date_range_filters_by_created_at(client, admin_user, customer_user):
    from datetime import datetime, timedelta, timezone
    from app.models.user import User as UserModel

    await _login_admin(client, admin_user)

    async with TestSessionLocal() as db:
        user = await db.get(UserModel, customer_user.id)
        user.created_at = datetime.now(timezone.utc) - timedelta(days=30)
        await db.commit()

    new_customer = await _create_user(
        email="fresh@example.com", name="Fresh Customer",
        password_hash=hash_password("x"), role="customer", email_verified=True, is_active=True,
    )

    today = datetime.now(timezone.utc).date().isoformat()
    resp = await client.get("/api/customers", params={"date_from": today})
    assert resp.status_code == 200, resp.text
    emails = [c["email"] for c in resp.json()]
    assert "fresh@example.com" in emails
    assert "lena@example.com" not in emails

    ten_days_ago = (datetime.now(timezone.utc).date() - timedelta(days=10)).isoformat()
    resp = await client.get("/api/customers", params={"date_to": ten_days_ago})
    assert resp.status_code == 200, resp.text
    emails = [c["email"] for c in resp.json()]
    assert "lena@example.com" in emails
    assert "fresh@example.com" not in emails


async def test_date_range_rejects_invalid_dates(client, admin_user):
    await _login_admin(client, admin_user)
    resp = await client.get("/api/customers", params={"date_from": "not-a-date"})
    assert resp.status_code == 400


async def test_export_csv_matches_filters_and_requires_manage_permission(client, admin_user, staff_user, customer_user):
    await _login_admin(client, admin_user)
    resp = await client.get("/api/customers/export", params={"is_active": "true"})
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("text/csv")
    assert "attachment" in resp.headers["content-disposition"]
    body = resp.text
    assert "lena@example.com" in body
    assert body.startswith("ID,Name,Email,Email Verified,Status,Created At")
    # Staff/admin rows are never in this export -- the underlying query
    # is scoped to role == 'customer', same as the list endpoint.
    assert "staffer@example.com" not in body
    assert "admin@eddyartgallery.app" not in body

    await client.post("/api/auth/logout")
    await _login_staff(client, staff_user)
    resp = await client.get("/api/customers/export")
    assert resp.status_code == 403
