"""
Comments end to end: guest comment -> nested reply -> tree shape on GET ->
staff can't moderate (needs comments:moderate, which staff has -- so this
also checks a *customer* can't) -> admin flags -> admin deletes a parent
and its replies cascade -> comments only attach to published photos.
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
            category=kwargs.get("category", "Test"),
            description="",
            specs=[],
            status=kwargs.get("status", "published"),
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
async def customer_user():
    return await _create_user(
        email="lena@example.com", name="Lena Ortiz",
        password_hash=hash_password("customer-pass-1"),
        role="customer", email_verified=True, is_active=True,
    )


@pytest_asyncio.fixture
async def published_photo():
    return await _create_photo(title="Pulse Band 3")


async def _login_admin(client, admin_user):
    await client.post("/api/auth/login", json={"email": "admin@eddyartgallery.app", "password": "super-secret-admin-1"})


async def _login_customer(client, customer_user):
    await client.post("/api/customer/login", json={"email": "lena@example.com", "password": "customer-pass-1"})


async def test_guest_comment_and_customer_reply_build_a_tree(client, published_photo, customer_user):
    resp = await client.post(f"/api/photos/{published_photo.id}/comments", json={"text": "Nice watch!"})
    assert resp.status_code == 201, resp.text
    root = resp.json()
    assert root["author"] == "Anonymous User"
    assert root["authorId"] is None
    assert root["flagged"] is False

    await _login_customer(client, customer_user)
    resp = await client.post(
        f"/api/photos/{published_photo.id}/comments",
        json={"text": "Agreed!", "parent_id": root["id"]},
    )
    assert resp.status_code == 201
    reply = resp.json()
    assert reply["author"] == "Lena Ortiz"
    assert reply["authorId"] == customer_user.id

    resp = await client.get(f"/api/photos/{published_photo.id}/comments")
    assert resp.status_code == 200
    tree = resp.json()
    assert len(tree) == 1
    assert tree[0]["id"] == root["id"]
    assert len(tree[0]["replies"]) == 1
    assert tree[0]["replies"][0]["id"] == reply["id"]


async def test_cannot_comment_on_draft_or_nonexistent_photo(client):
    draft_photo = await _create_photo(title="Draft Item", status="draft")

    resp = await client.post(f"/api/photos/{draft_photo.id}/comments", json={"text": "hi"})
    assert resp.status_code == 404

    resp = await client.post("/api/photos/does-not-exist/comments", json={"text": "hi"})
    assert resp.status_code == 404

    resp = await client.get(f"/api/photos/{draft_photo.id}/comments")
    assert resp.status_code == 404


async def test_invalid_parent_id_rejected(client, published_photo):
    resp = await client.post(
        f"/api/photos/{published_photo.id}/comments",
        json={"text": "hi", "parent_id": "not-a-real-comment"},
    )
    assert resp.status_code == 400


async def test_customer_cannot_moderate(client, published_photo, customer_user):
    resp = await client.post(f"/api/photos/{published_photo.id}/comments", json={"text": "spam?"})
    comment_id = resp.json()["id"]

    await _login_customer(client, customer_user)

    resp = await client.get("/api/comments")
    assert resp.status_code == 401

    resp = await client.patch(f"/api/comments/{comment_id}", json={"flagged": True})
    assert resp.status_code == 401

    resp = await client.delete(f"/api/comments/{comment_id}")
    assert resp.status_code == 401


async def test_admin_flag_and_flat_cross_photo_list(client, published_photo, admin_user):
    resp = await client.post(f"/api/photos/{published_photo.id}/comments", json={"text": "check this out"})
    comment_id = resp.json()["id"]

    await _login_admin(client, admin_user)

    resp = await client.get("/api/comments")
    assert resp.status_code == 200
    flat = resp.json()
    assert any(c["id"] == comment_id for c in flat)
    match = next(c for c in flat if c["id"] == comment_id)
    assert match["photoId"] == published_photo.id
    assert match["photoTitle"] == published_photo.title
    assert match["flagged"] is False

    resp = await client.patch(f"/api/comments/{comment_id}", json={"flagged": True})
    assert resp.status_code == 200

    resp = await client.get("/api/comments")
    match = next(c for c in resp.json() if c["id"] == comment_id)
    assert match["flagged"] is True

    # Flagging doesn't hide it from the public tree -- matches the existing
    # admin UI, which treats "flagged" as a moderation marker, not removal.
    resp = await client.get(f"/api/photos/{published_photo.id}/comments")
    assert any(c["id"] == comment_id for c in resp.json())


async def test_delete_cascades_to_replies(client, published_photo, admin_user):
    resp = await client.post(f"/api/photos/{published_photo.id}/comments", json={"text": "root"})
    root_id = resp.json()["id"]
    resp = await client.post(
        f"/api/photos/{published_photo.id}/comments", json={"text": "reply", "parent_id": root_id}
    )
    reply_id = resp.json()["id"]

    await _login_admin(client, admin_user)
    resp = await client.delete(f"/api/comments/{root_id}")
    assert resp.status_code == 200

    resp = await client.get("/api/comments")
    ids = [c["id"] for c in resp.json()]
    assert root_id not in ids
    assert reply_id not in ids


async def test_comment_rate_limit(client, published_photo):
    from app.routers.comments import COMMENT_RATE_LIMIT_MAX_ATTEMPTS

    for _ in range(COMMENT_RATE_LIMIT_MAX_ATTEMPTS):
        resp = await client.post(f"/api/photos/{published_photo.id}/comments", json={"text": "spam"})
        assert resp.status_code == 201

    resp = await client.post(f"/api/photos/{published_photo.id}/comments", json={"text": "one too many"})
    assert resp.status_code == 429
