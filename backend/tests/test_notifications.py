"""
Notifications end to end, including the two real trigger points: a reply
to a comment notifies the parent's author (unless it's a guest parent or
you're replying to yourself), and an admin/staff conversation reply
notifies the customer. Plus the notifications API itself: list, unread
count, mark-one-read, mark-all-read, and that one customer can't see or
touch another's notifications.
"""

import pytest
import pytest_asyncio

from app.core.security import hash_password
from app.models.photo import Photo
from app.models.user import User
from tests.conftest import TestSessionLocal


async def _create_user(**kwargs) -> User:
    async with TestSessionLocal() as db:
        user = User(**kwargs)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user


async def _create_photo(**kwargs) -> Photo:
    async with TestSessionLocal() as db:
        photo = Photo(
            object_key=f"photos/{kwargs.get('title', 'x')}.jpg",
            title=kwargs.get("title", "Test Photo"),
            category="Test",
            description="",
            specs=[],
            status="published",
        )
        db.add(photo)
        await db.commit()
        await db.refresh(photo)
        return photo


@pytest_asyncio.fixture
async def admin_user():
    return await _create_user(
        email="admin@eddyartgallery.app", name="Admin",
        password_hash=hash_password("super-secret-admin-1"),
        role="admin", email_verified=True, is_active=True,
    )


@pytest_asyncio.fixture
async def lena():
    return await _create_user(
        email="lena@example.com", name="Lena Ortiz",
        password_hash=hash_password("customer-pass-1"),
        role="customer", email_verified=True, is_active=True,
    )


@pytest_asyncio.fixture
async def omar():
    return await _create_user(
        email="omar@example.com", name="Omar Haddad",
        password_hash=hash_password("customer-pass-2"),
        role="customer", email_verified=True, is_active=True,
    )


@pytest_asyncio.fixture
async def published_photo():
    return await _create_photo(title="Pulse Band 3")


async def _login_admin(client, admin_user):
    await client.post("/api/auth/login", json={"email": "admin@eddyartgallery.app", "password": "super-secret-admin-1"})


async def _login(client, email, password):
    await client.post("/api/customer/login", json={"email": email, "password": password})


async def test_comment_reply_notifies_parent_author(client, published_photo, lena, omar):
    await _login(client, "lena@example.com", "customer-pass-1")
    resp = await client.post(f"/api/photos/{published_photo.id}/comments", json={"text": "Nice watch!"})
    root_id = resp.json()["id"]
    await client.post("/api/customer/logout")

    await _login(client, "omar@example.com", "customer-pass-2")
    await client.post(f"/api/photos/{published_photo.id}/comments", json={"text": "Agreed!", "parent_id": root_id})
    await client.post("/api/customer/logout")

    await _login(client, "lena@example.com", "customer-pass-1")
    resp = await client.get("/api/notifications")
    assert resp.status_code == 200
    notifications = resp.json()
    assert len(notifications) == 1
    assert notifications[0]["type"] == "comment_reply"
    assert "Omar Haddad" in notifications[0]["message"]
    assert notifications[0]["href"] == f"/image/{published_photo.id}"
    assert notifications[0]["read"] is False


async def test_no_self_notification_or_guest_notification(client, published_photo, lena):
    resp = await client.post(f"/api/photos/{published_photo.id}/comments", json={"text": "guest comment"})
    root_id = resp.json()["id"]

    await _login(client, "lena@example.com", "customer-pass-1")
    await client.post(f"/api/photos/{published_photo.id}/comments", json={"text": "reply", "parent_id": root_id})
    resp = await client.get("/api/notifications")
    assert resp.json() == []

    resp = await client.post(f"/api/photos/{published_photo.id}/comments", json={"text": "my own comment"})
    my_comment_id = resp.json()["id"]
    await client.post(f"/api/photos/{published_photo.id}/comments", json={"text": "replying to myself", "parent_id": my_comment_id})

    resp = await client.get("/api/notifications")
    assert resp.json() == []


async def test_admin_conversation_reply_notifies_customer(client, admin_user, lena):
    await _login(client, "lena@example.com", "customer-pass-1")
    resp = await client.post("/api/conversations", json={"subject": "Licensing", "text": "hello"})
    conv_id = resp.json()["id"]
    await client.post("/api/customer/logout")

    await _login_admin(client, admin_user)
    await client.post(f"/api/conversations/{conv_id}/messages", json={"text": "Here are our rates."})
    await client.post("/api/auth/logout")

    await _login(client, "lena@example.com", "customer-pass-1")
    resp = await client.get("/api/notifications")
    notifications = resp.json()
    assert len(notifications) == 1
    assert notifications[0]["type"] == "conversation_reply"
    assert "Admin" in notifications[0]["message"]
    assert notifications[0]["href"] == "/dashboard/inbox"


async def test_customer_reply_to_own_conversation_does_not_self_notify(client, lena):
    await _login(client, "lena@example.com", "customer-pass-1")
    resp = await client.post("/api/conversations", json={"subject": "x", "text": "y"})
    conv_id = resp.json()["id"]
    await client.post(f"/api/conversations/{conv_id}/messages", json={"text": "following up"})

    resp = await client.get("/api/notifications")
    assert resp.json() == []


async def test_unread_count_and_mark_read(client, published_photo, lena, omar):
    await _login(client, "lena@example.com", "customer-pass-1")
    resp = await client.post(f"/api/photos/{published_photo.id}/comments", json={"text": "c1"})
    c1 = resp.json()["id"]
    resp = await client.post(f"/api/photos/{published_photo.id}/comments", json={"text": "c2"})
    c2 = resp.json()["id"]
    await client.post("/api/customer/logout")

    await _login(client, "omar@example.com", "customer-pass-2")
    await client.post(f"/api/photos/{published_photo.id}/comments", json={"text": "r1", "parent_id": c1})
    await client.post(f"/api/photos/{published_photo.id}/comments", json={"text": "r2", "parent_id": c2})
    await client.post("/api/customer/logout")

    await _login(client, "lena@example.com", "customer-pass-1")
    resp = await client.get("/api/notifications/unread-count")
    assert resp.json() == {"count": 2}

    notifications = (await client.get("/api/notifications")).json()
    resp = await client.post(f"/api/notifications/{notifications[0]['id']}/read")
    assert resp.status_code == 200
    assert resp.json()["read"] is True

    resp = await client.get("/api/notifications/unread-count")
    assert resp.json() == {"count": 1}

    resp = await client.post("/api/notifications/read-all")
    assert resp.status_code == 200
    resp = await client.get("/api/notifications/unread-count")
    assert resp.json() == {"count": 0}


async def test_customer_cannot_see_or_mark_another_customers_notification(client, published_photo, lena, omar):
    await _login(client, "lena@example.com", "customer-pass-1")
    resp = await client.post(f"/api/photos/{published_photo.id}/comments", json={"text": "c1"})
    c1 = resp.json()["id"]
    await client.post("/api/customer/logout")

    await _login(client, "omar@example.com", "customer-pass-2")
    await client.post(f"/api/photos/{published_photo.id}/comments", json={"text": "reply", "parent_id": c1})
    await client.post("/api/customer/logout")

    await _login(client, "lena@example.com", "customer-pass-1")
    notification_id = (await client.get("/api/notifications")).json()[0]["id"]
    await client.post("/api/customer/logout")

    await _login(client, "omar@example.com", "customer-pass-2")
    resp = await client.get("/api/notifications")
    assert resp.json() == []

    resp = await client.post(f"/api/notifications/{notification_id}/read")
    assert resp.status_code == 404
