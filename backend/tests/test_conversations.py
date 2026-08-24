"""
Conversations end to end: customer starts a thread -> admin sees it in the
cross-customer list -> admin replies (status auto-flips new -> in_progress)
-> customer sees the reply in their own list -> customer replies back ->
admin marks resolved -> permission boundaries (customer can't list
everyone's conversations or reply to someone else's; both admin and staff
have requests:respond by default, so this also checks a *customer* can't
use the admin endpoints).
"""

import pytest
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
async def customer_user():
    return await _create_user(
        email="lena@example.com", name="Lena Ortiz",
        password_hash=hash_password("customer-pass-1"),
        role="customer", email_verified=True, is_active=True,
    )


@pytest_asyncio.fixture
async def other_customer():
    return await _create_user(
        email="omar@example.com", name="Omar Haddad",
        password_hash=hash_password("customer-pass-2"),
        role="customer", email_verified=True, is_active=True,
    )


async def _login_admin(client, admin_user):
    await client.post("/api/auth/login", json={"email": "admin@eddyartgallery.app", "password": "super-secret-admin-1"})


async def _login_customer(client, customer_user):
    await client.post("/api/customer/login", json={"email": "lena@example.com", "password": "customer-pass-1"})


async def _login_other_customer(client, other_customer):
    await client.post("/api/customer/login", json={"email": "omar@example.com", "password": "customer-pass-2"})


async def test_full_conversation_lifecycle(client, customer_user, admin_user):
    await _login_customer(client, customer_user)
    resp = await client.post(
        "/api/conversations", json={"subject": "Bulk licensing inquiry", "text": "What are your commercial terms?"}
    )
    assert resp.status_code == 201, resp.text
    conv = resp.json()
    assert conv["status"] == "new"
    assert conv["customerName"] == "Lena Ortiz"
    assert len(conv["messages"]) == 1
    assert conv["messages"][0]["senderRole"] == "customer"
    conv_id = conv["id"]

    resp = await client.get("/api/conversations/mine")
    assert resp.status_code == 200
    assert any(c["id"] == conv_id for c in resp.json())
    await client.post("/api/customer/logout")

    await _login_admin(client, admin_user)
    resp = await client.get("/api/conversations")
    assert resp.status_code == 200
    assert any(c["id"] == conv_id for c in resp.json())

    resp = await client.post(f"/api/conversations/{conv_id}/messages", json={"text": "Commercial licensing starts at $80/image."})
    assert resp.status_code == 200
    conv = resp.json()
    assert conv["status"] == "in_progress"  # auto-flipped by the admin reply
    assert len(conv["messages"]) == 2
    assert conv["messages"][1]["senderName"] == "Admin"
    await client.post("/api/auth/logout")

    await _login_customer(client, customer_user)
    resp = await client.get("/api/conversations/mine")
    conv = next(c for c in resp.json() if c["id"] == conv_id)
    assert len(conv["messages"]) == 2

    resp = await client.post(f"/api/conversations/{conv_id}/messages", json={"text": "Great, sending our catalog over."})
    assert resp.status_code == 200
    assert len(resp.json()["messages"]) == 3
    await client.post("/api/customer/logout")

    await _login_admin(client, admin_user)
    resp = await client.patch(f"/api/conversations/{conv_id}", json={"status": "resolved"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "resolved"


async def test_customer_cannot_use_admin_endpoints(client, customer_user):
    await _login_customer(client, customer_user)

    resp = await client.get("/api/conversations")
    assert resp.status_code == 403

    resp = await client.post("/api/conversations", json={"subject": "x", "text": "y"})
    conv_id = resp.json()["id"]

    resp = await client.patch(f"/api/conversations/{conv_id}", json={"status": "resolved"})
    assert resp.status_code == 403


async def test_customer_cannot_reply_to_someone_elses_conversation(client, customer_user, other_customer):
    await _login_customer(client, customer_user)
    resp = await client.post("/api/conversations", json={"subject": "Private", "text": "hello"})
    conv_id = resp.json()["id"]
    await client.post("/api/customer/logout")

    await _login_other_customer(client, other_customer)
    resp = await client.post(f"/api/conversations/{conv_id}/messages", json={"text": "sneaky reply"})
    assert resp.status_code == 403

    resp = await client.get("/api/conversations/mine")
    assert all(c["id"] != conv_id for c in resp.json())


async def test_conversation_not_found(client, admin_user):
    await _login_admin(client, admin_user)
    resp = await client.post("/api/conversations/does-not-exist/messages", json={"text": "hi"})
    assert resp.status_code == 404

    resp = await client.patch("/api/conversations/does-not-exist", json={"status": "resolved"})
    assert resp.status_code == 404


async def test_staff_has_same_access_as_admin(client, admin_user, customer_user):
    staff = await _create_user(
        email="jordan@example.com", name="Jordan Blake",
        password_hash=hash_password("staff-pass-1"),
        role="staff", email_verified=True, is_active=True,
    )

    await _login_customer(client, customer_user)
    resp = await client.post("/api/conversations", json={"subject": "Partnership", "text": "hello"})
    conv_id = resp.json()["id"]
    await client.post("/api/customer/logout")

    await client.post("/api/auth/login", json={"email": "jordan@example.com", "password": "staff-pass-1"})
    resp = await client.get("/api/conversations")
    assert resp.status_code == 200
    assert any(c["id"] == conv_id for c in resp.json())

    resp = await client.post(f"/api/conversations/{conv_id}/messages", json={"text": "Forwarding to our lead."})
    assert resp.status_code == 200
    assert resp.json()["messages"][-1]["senderName"] == "Jordan Blake"
    assert resp.json()["messages"][-1]["senderRole"] == "staff"
