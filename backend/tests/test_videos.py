"""
Video management end to end -- mirrors test_photos.py's coverage
(upload-url -> create -> public visibility rules -> view count dedup ->
like/unlike -> edit -> delete with storage cleanup -> permission
boundaries) PLUS the two things that make videos different from photos:
size and duration enforcement, since those are the actual point of this
feature (see app/core/config.py's MAX_VIDEO_SIZE_BYTES /
MAX_VIDEO_DURATION_SECONDS).

Storage itself is monkeypatched (see `fake_storage` below) -- there's no
real bucket in tests. The REAL enforcement boundary (Supabase's bucket-
level file_size_limit) can't be exercised without a real Supabase
project, so what's tested here is the backend's own defense-in-depth
checks in get_upload_url/create_video -- see those functions' docstrings
for why both layers exist and which one actually matters most.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.core.security import hash_password
from app.main import app
from app.models.user import User
from tests.conftest import TestSessionLocal

settings = get_settings()


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
    """Patched at the router module level -- same reasoning as
    test_photos.py's fake_storage fixture."""
    import app.routers.videos as videos_module

    deleted_keys: list[str] = []
    _counter = {"n": 0}

    def _fake_generate_object_key(filename: str, prefix: str = "videos") -> str:
        _counter["n"] += 1
        return f"{prefix}/fake-{_counter['n']}-{filename}"

    def _fake_presigned_url(object_key: str, content_type: str, expires_in: int = 300, bucket=None) -> str:
        return f"https://fake-r2.example.com/{bucket}/{object_key}?signature=fake"

    def _fake_public_url(object_key: str, bucket=None) -> str:
        return f"https://media.example.com/{bucket}/{object_key}"

    def _fake_delete_object(object_key: str, bucket=None) -> bool:
        deleted_keys.append((bucket, object_key))
        return True

    monkeypatch.setattr(videos_module, "generate_object_key", _fake_generate_object_key)
    monkeypatch.setattr(videos_module, "generate_presigned_upload_url", _fake_presigned_url)
    monkeypatch.setattr(videos_module, "public_url", _fake_public_url)
    monkeypatch.setattr(videos_module, "delete_object", _fake_delete_object)

    return deleted_keys


async def _new_client() -> AsyncClient:
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


async def _admin_client() -> AsyncClient:
    c = await _new_client()
    resp = await c.post("/api/auth/login", json={"email": "admin@eddyartgallery.app", "password": "super-secret-admin-1"})
    assert resp.status_code == 200, resp.text
    return c


async def _customer_client() -> AsyncClient:
    c = await _new_client()
    resp = await c.post("/api/customer/login", json={"email": "lena@example.com", "password": "customer-pass-1"})
    assert resp.status_code == 200, resp.text
    return c


async def _upload_video(
    admin_client, title, *, size_bytes=2_000_000, duration_seconds=6.0, category="Product Demos"
) -> dict:
    resp = await admin_client.post(
        "/api/videos/upload-url",
        json={
            "filename": "demo.mp4", "content_type": "video/mp4",
            "size_bytes": size_bytes, "duration_seconds": duration_seconds,
        },
    )
    assert resp.status_code == 200, resp.text
    object_key = resp.json()["objectKey"]

    resp = await admin_client.post(
        "/api/videos",
        json={
            "objectKey": object_key,
            "title": title,
            "category": category,
            "description": "A short product demo clip.",
            "specs": ["720p"],
            "durationSeconds": duration_seconds,
            "mimeType": "video/mp4",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ============================================================
# Size and duration enforcement -- the actual point of this feature
# ============================================================


async def test_oversized_video_rejected_at_upload_url_step(admin_user):
    admin = await _admin_client()
    try:
        resp = await admin.post(
            "/api/videos/upload-url",
            json={
                "filename": "big.mp4", "content_type": "video/mp4",
                "size_bytes": settings.MAX_VIDEO_SIZE_BYTES + 1, "duration_seconds": 5.0,
            },
        )
        assert resp.status_code == 400
        assert "size" in resp.json()["detail"].lower()
    finally:
        await admin.aclose()


async def test_video_at_exactly_the_size_limit_is_accepted(admin_user, fake_storage):
    admin = await _admin_client()
    try:
        video = await _upload_video(admin, "Exactly at the limit", size_bytes=settings.MAX_VIDEO_SIZE_BYTES)
        assert video["title"] == "Exactly at the limit"
    finally:
        await admin.aclose()


async def test_too_long_video_rejected_at_upload_url_step(admin_user):
    admin = await _admin_client()
    try:
        resp = await admin.post(
            "/api/videos/upload-url",
            json={
                "filename": "long.mp4", "content_type": "video/mp4",
                "size_bytes": 1_000_000, "duration_seconds": settings.MAX_VIDEO_DURATION_SECONDS + 0.1,
            },
        )
        assert resp.status_code == 400
        assert "duration" in resp.json()["detail"].lower()
    finally:
        await admin.aclose()


async def test_video_at_exactly_the_duration_limit_is_accepted(admin_user, fake_storage):
    admin = await _admin_client()
    try:
        video = await _upload_video(admin, "Exactly at the limit", duration_seconds=settings.MAX_VIDEO_DURATION_SECONDS)
        assert video["durationSeconds"] == settings.MAX_VIDEO_DURATION_SECONDS
    finally:
        await admin.aclose()


async def test_too_long_video_rejected_even_if_it_slips_past_the_first_check(admin_user):
    """The upload-url step only sees a pre-upload CLAIM about duration --
    create_video re-checks the real value reported for the file that
    actually finished uploading. This test skips straight to create_video
    with an over-limit duration, simulating a client that lied (or was
    wrong) at the first step, to confirm the second check is real and not
    just a duplicate of the first."""
    admin = await _admin_client()
    try:
        resp = await admin.post(
            "/api/videos",
            json={
                "objectKey": "videos/whatever.mp4",
                "title": "Snuck past step 1", "category": "Product Demos",
                "durationSeconds": settings.MAX_VIDEO_DURATION_SECONDS + 5,
                "mimeType": "video/mp4",
            },
        )
        assert resp.status_code == 400
        assert "duration" in resp.json()["detail"].lower()
    finally:
        await admin.aclose()


async def test_non_mp4_content_type_rejected(admin_user):
    admin = await _admin_client()
    try:
        resp = await admin.post(
            "/api/videos/upload-url",
            json={
                "filename": "demo.mov", "content_type": "video/quicktime",
                "size_bytes": 1_000_000, "duration_seconds": 5.0,
            },
        )
        assert resp.status_code == 400
        assert "type" in resp.json()["detail"].lower()
    finally:
        await admin.aclose()


# ============================================================
# Full admin lifecycle -- mirrors test_photos.py's equivalent
# ============================================================


async def test_video_management_full_admin_lifecycle(client, admin_user, customer_user, fake_storage):
    admin = await _admin_client()
    try:
        video = await _upload_video(admin, "Product Demo Clip")
        assert video["status"] == "draft"
        assert video["durationSeconds"] == 6.0
        assert video["poster"] is None

        anon_list = (await client.get("/api/videos")).json()
        assert video["id"] not in [v["id"] for v in anon_list]

        resp = await admin.patch(f"/api/videos/{video['id']}", json={"status": "published"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "published"

        customer = await _customer_client()
        try:
            resp = await customer.get(f"/api/videos/{video['id']}")
            assert resp.status_code == 200
            assert resp.json()["viewCount"] == 1

            resp = await customer.get(f"/api/videos/{video['id']}")
            assert resp.json()["viewCount"] == 1  # not double-counted

            resp = await customer.post(f"/api/videos/{video['id']}/like")
            assert resp.status_code == 200
            assert resp.json() == {"liked": True, "likeCount": 1}
        finally:
            await customer.aclose()

        admin_list = (await admin.get("/api/videos", params={"limit": 100})).json()
        same = next(v for v in admin_list if v["id"] == video["id"])
        assert same["viewCount"] == 1
        assert same["likeCount"] == 1

        resp = await admin.patch(f"/api/videos/{video['id']}", json={"status": "flagged"})
        assert resp.status_code == 200

        admin_get = await admin.get(f"/api/videos/{video['id']}")
        assert admin_get.status_code == 200  # staff/admin can still see a flagged video

        resp = await admin.patch(
            f"/api/videos/{video['id']}",
            json={"status": "published", "title": "Product Demo (V2)", "category": "Featured"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "published"
        assert body["title"] == "Product Demo (V2)"
        assert body["viewCount"] == 1  # survived the metadata edit
        assert body["likeCount"] == 1

        resp = await admin.delete(f"/api/videos/{video['id']}")
        assert resp.status_code == 200

        deleted_bucket, deleted_key = fake_storage[-1]
        assert deleted_bucket == settings.SUPABASE_VIDEO_BUCKET
        assert deleted_key in video["video"]

        resp = await admin.get(f"/api/videos/{video['id']}")
        assert resp.status_code == 404
    finally:
        await admin.aclose()


async def test_video_poster_upload_and_deletion(admin_user, fake_storage):
    """Poster lives in the PHOTOS bucket (it's a still image) -- confirm
    it round-trips correctly and gets cleaned up (from the photos
    bucket, not the videos bucket) on delete."""
    admin = await _admin_client()
    try:
        resp = await admin.post(
            "/api/videos/upload-url",
            json={"filename": "demo.mp4", "content_type": "video/mp4", "size_bytes": 1_000_000, "duration_seconds": 5.0},
        )
        object_key = resp.json()["objectKey"]

        resp = await admin.post(
            "/api/videos",
            json={
                "objectKey": object_key, "posterObjectKey": "photos/fake-poster.jpg",
                "title": "With poster", "category": "Product Demos",
                "durationSeconds": 5.0, "mimeType": "video/mp4",
            },
        )
        assert resp.status_code == 201
        video = resp.json()
        assert video["poster"] is not None
        assert "fake-poster.jpg" in video["poster"]

        await admin.delete(f"/api/videos/{video['id']}")
        deleted_buckets_and_keys = fake_storage
        # Both the video object (videos bucket) and the poster (photos
        # bucket, i.e. bucket=None -> default) should have been deleted.
        assert any(b == settings.SUPABASE_VIDEO_BUCKET for b, k in deleted_buckets_and_keys)
        assert any(b is None and "fake-poster.jpg" in k for b, k in deleted_buckets_and_keys)
    finally:
        await admin.aclose()


async def test_customer_cannot_manage_videos(admin_user, customer_user, fake_storage):
    """Matches test_photos.py's test_customer_cannot_manage_photos: 401,
    not 403 -- require_permission's dependency chain checks the
    admin/staff session cookie first (get_current_staff_or_admin), and a
    customer session uses a completely different cookie, so it fails
    authentication (401) before ever reaching the permission check
    (403, which is for an authenticated admin/staff user who lacks a
    specific permission -- not applicable here)."""
    admin = await _admin_client()
    customer = await _customer_client()
    try:
        video = await _upload_video(admin, "Admin's video")
        await admin.patch(f"/api/videos/{video['id']}", json={"status": "published"})

        resp = await customer.post(
            "/api/videos/upload-url",
            json={"filename": "x.mp4", "content_type": "video/mp4", "size_bytes": 1000, "duration_seconds": 3.0},
        )
        assert resp.status_code == 401

        resp = await customer.patch(f"/api/videos/{video['id']}", json={"title": "Hacked"})
        assert resp.status_code == 401

        resp = await customer.delete(f"/api/videos/{video['id']}")
        assert resp.status_code == 401
    finally:
        await admin.aclose()
        await customer.aclose()


async def test_flagged_video_hidden_from_public(client, admin_user):
    admin = await _admin_client()
    try:
        video = await _upload_video(admin, "Will be flagged")
        await admin.patch(f"/api/videos/{video['id']}", json={"status": "published"})
        await admin.patch(f"/api/videos/{video['id']}", json={"status": "flagged"})

        public_list = (await client.get("/api/videos")).json()
        assert video["id"] not in [v["id"] for v in public_list]

        public_get = await client.get(f"/api/videos/{video['id']}")
        assert public_get.status_code == 404
    finally:
        await admin.aclose()


# ============================================================
# Comments on videos -- confirms Comment.video_id works end to end,
# alongside (not instead of) the existing photo comment path.
# ============================================================


async def test_comments_on_a_video_end_to_end(admin_user, customer_user):
    admin = await _admin_client()
    customer = await _customer_client()
    try:
        video = await _upload_video(admin, "Commentable video")
        await admin.patch(f"/api/videos/{video['id']}", json={"status": "published"})

        resp = await customer.post(f"/api/videos/{video['id']}/comments", json={"text": "Great clip!"})
        assert resp.status_code == 201, resp.text
        comment = resp.json()
        assert comment["author"] == "Lena Ortiz"

        resp = await customer.get(f"/api/videos/{video['id']}/comments")
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["text"] == "Great clip!"

        # Cross-media moderation list includes it with videoId/videoTitle set.
        admin_comments = (await admin.get("/api/comments")).json()
        matching = next(c for c in admin_comments if c["id"] == comment["id"])
        assert matching["videoId"] == video["id"]
        assert matching["videoTitle"] == "Commentable video"
        assert matching["photoId"] is None
    finally:
        await admin.aclose()
        await customer.aclose()


async def test_cannot_comment_on_draft_or_nonexistent_video(client, admin_user):
    admin = await _admin_client()
    try:
        video = await _upload_video(admin, "Still a draft")  # never published
        resp = await client.post(f"/api/videos/{video['id']}/comments", json={"text": "Hi"})
        assert resp.status_code == 404

        resp = await client.post("/api/videos/nonexistent-id/comments", json={"text": "Hi"})
        assert resp.status_code == 404
    finally:
        await admin.aclose()
