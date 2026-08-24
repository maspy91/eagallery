"""
Photo management end to end: upload-url -> create -> public visibility
rules (draft/flagged hidden from the public, visible to staff) -> view
count dedup -> like/unlike -> edit -> delete (with storage cleanup) ->
permission boundaries (customer can't manage photos, staff can).

Storage itself is monkeypatched (see `fake_storage` below) -- there's no
real bucket in tests, only the DB side of things and the calls made to
the storage module are exercised.
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


@pytest.fixture(autouse=True)
def fake_storage(monkeypatch):
    """Patched at the router module level -- same `from X import Y` name-
    binding reasoning as the redis_client/email patches in conftest.py."""
    import app.routers.photos as photos_module

    deleted_keys: list[str] = []

    def _fake_generate_object_key(filename: str, prefix: str = "photos") -> str:
        return f"{prefix}/fake-{filename}"

    def _fake_presigned_url(object_key: str, content_type: str, expires_in: int = 300) -> str:
        return f"https://fake-r2.example.com/{object_key}?signature=fake"

    def _fake_public_url(object_key: str) -> str:
        return f"https://media.example.com/{object_key}"

    def _fake_delete_object(object_key: str) -> None:
        deleted_keys.append(object_key)

    monkeypatch.setattr(photos_module, "generate_object_key", _fake_generate_object_key)
    monkeypatch.setattr(photos_module, "generate_presigned_upload_url", _fake_presigned_url)
    monkeypatch.setattr(photos_module, "public_url", _fake_public_url)
    monkeypatch.setattr(photos_module, "delete_object", _fake_delete_object)

    return deleted_keys


async def _login_admin(client, admin_user):
    await client.post("/api/auth/login", json={"email": "admin@eddyartgallery.app", "password": "super-secret-admin-1"})


async def _login_customer(client, customer_user):
    await client.post("/api/customer/login", json={"email": "lena@example.com", "password": "customer-pass-1"})


async def _upload_and_create_photo(client, title="Pulse Band 3") -> str:
    resp = await client.post(
        "/api/photos/upload-url", json={"filename": "watch.jpg", "content_type": "image/jpeg"}
    )
    assert resp.status_code == 200, resp.text
    object_key = resp.json()["objectKey"]

    resp = await client.post(
        "/api/photos",
        json={
            "objectKey": object_key,
            "title": title,
            "category": "Wearable Tech",
            "description": "A fitness band.",
            "specs": ["10-Day Battery", "Water Resistant"],
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def test_upload_and_publish_lifecycle(client, admin_user):
    await _login_admin(client, admin_user)

    photo_id = await _upload_and_create_photo(client)

    # Newly created photos are drafts -- invisible to the public.
    await client.post("/api/auth/logout")
    resp = await client.get("/api/photos")
    assert resp.status_code == 200
    assert all(p["id"] != photo_id for p in resp.json())

    resp = await client.get(f"/api/photos/{photo_id}")
    assert resp.status_code == 404  # drafts 404 for the public, not 403

    # Staff/admin can still see it (and filter by status).
    await _login_admin(client, admin_user)
    resp = await client.get("/api/photos", params={"status": "draft"})
    assert resp.status_code == 200
    assert any(p["id"] == photo_id for p in resp.json())

    # Publish it.
    resp = await client.patch(f"/api/photos/{photo_id}", json={"status": "published"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "published"

    # Now the public can see and fetch it, and the first fetch bumps the
    # view count -- a second fetch from the same (test-client) IP does
    # NOT bump it again, since guest views are deduped by IP now.
    await client.post("/api/auth/logout")
    resp = await client.get(f"/api/photos/{photo_id}")
    assert resp.status_code == 200
    assert resp.json()["viewCount"] == 1

    resp = await client.get(f"/api/photos/{photo_id}")
    assert resp.json()["viewCount"] == 1


async def test_customer_cannot_manage_photos(client, customer_user):
    await _login_customer(client, customer_user)

    resp = await client.post(
        "/api/photos/upload-url", json={"filename": "x.jpg", "content_type": "image/jpeg"}
    )
    assert resp.status_code == 403

    resp = await client.post(
        "/api/photos",
        json={"objectKey": "photos/x.jpg", "title": "X", "category": "Y", "description": "", "specs": []},
    )
    assert resp.status_code == 403


async def test_like_toggle(client, admin_user, customer_user):
    await _login_admin(client, admin_user)
    photo_id = await _upload_and_create_photo(client)
    await client.patch(f"/api/photos/{photo_id}", json={"status": "published"})
    await client.post("/api/auth/logout")

    # Anonymous / not-logged-in customers can't like.
    resp = await client.post(f"/api/photos/{photo_id}/like")
    assert resp.status_code == 401

    await _login_customer(client, customer_user)

    resp = await client.post(f"/api/photos/{photo_id}/like")
    assert resp.status_code == 200
    assert resp.json() == {"liked": True, "likeCount": 1}

    resp = await client.get(f"/api/photos/{photo_id}")
    assert resp.json()["liked"] is True
    assert resp.json()["likeCount"] == 1

    # Toggling again unlikes.
    resp = await client.post(f"/api/photos/{photo_id}/like")
    assert resp.status_code == 200
    assert resp.json() == {"liked": False, "likeCount": 0}


async def test_random_selection_and_category_filter(client, admin_user):
    await _login_admin(client, admin_user)
    ids = []
    for i in range(5):
        pid = await _upload_and_create_photo(client, title=f"Item {i}")
        await client.patch(f"/api/photos/{pid}", json={"status": "published"})
        ids.append(pid)
    await client.post("/api/auth/logout")

    resp = await client.get("/api/photos", params={"random": 3})
    assert resp.status_code == 200
    assert len(resp.json()) == 3
    assert all(p["id"] in ids for p in resp.json())

    resp = await client.get("/api/photos", params={"category": "Wearable Tech"})
    assert resp.status_code == 200
    assert len(resp.json()) == 5


async def test_delete_removes_photo_and_calls_r2_cleanup(client, admin_user, fake_storage):
    await _login_admin(client, admin_user)
    photo_id = await _upload_and_create_photo(client)

    resp = await client.delete(f"/api/photos/{photo_id}")
    assert resp.status_code == 200

    resp = await client.get(f"/api/photos/{photo_id}", params={})
    assert resp.status_code == 404

    assert len(fake_storage) == 1  # delete_object was called once with the photo's object_key


async def test_flagged_photos_hidden_from_public(client, admin_user):
    await _login_admin(client, admin_user)
    photo_id = await _upload_and_create_photo(client)
    await client.patch(f"/api/photos/{photo_id}", json={"status": "published"})
    await client.patch(f"/api/photos/{photo_id}", json={"status": "flagged"})
    await client.post("/api/auth/logout")

    resp = await client.get(f"/api/photos/{photo_id}")
    assert resp.status_code == 404

    resp = await client.get("/api/photos")
    assert all(p["id"] != photo_id for p in resp.json())


async def test_view_count_deduped_per_logged_in_customer(client, admin_user, customer_user):
    await _login_admin(client, admin_user)
    photo_id = await _upload_and_create_photo(client)
    await client.patch(f"/api/photos/{photo_id}", json={"status": "published"})
    await client.post("/api/auth/logout")

    await _login_customer(client, customer_user)
    resp = await client.get(f"/api/photos/{photo_id}")
    assert resp.json()["viewCount"] == 1

    # Same customer, refresh -- doesn't count again.
    resp = await client.get(f"/api/photos/{photo_id}")
    assert resp.json()["viewCount"] == 1
    resp = await client.get(f"/api/photos/{photo_id}")
    assert resp.json()["viewCount"] == 1


async def test_admin_staff_preview_does_not_count_as_a_view(client, admin_user):
    await _login_admin(client, admin_user)
    photo_id = await _upload_and_create_photo(client)
    await client.patch(f"/api/photos/{photo_id}", json={"status": "published"})

    # Still logged in as admin -- viewing your own published photo
    # shouldn't inflate the public view count.
    resp = await client.get(f"/api/photos/{photo_id}")
    assert resp.json()["viewCount"] == 0
    resp = await client.get(f"/api/photos/{photo_id}")
    assert resp.json()["viewCount"] == 0

    # A real (guest) viewer after that is the first real view.
    await client.post("/api/auth/logout")
    resp = await client.get(f"/api/photos/{photo_id}")
    assert resp.json()["viewCount"] == 1
