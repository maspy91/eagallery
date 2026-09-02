"""
AI upload-assist (describe-media) end to end. The real Gemini API is
NEVER called in tests -- app.core.ai.generate_media_description is
monkeypatched at the module level the router imports it from (`ai_core`
in app/routers/ai.py), same pattern as fake_storage in
test_photos.py/test_videos.py. What's actually exercised is everything
this backend controls: permission checks, the objectKey-must-belong-to-a-
real-upload check, rate limiting, response parsing, and the
unconfigured/AI_API_KEY-unset 404 behavior.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.security import hash_password
from app.main import app
from app.models.photo import Photo
from app.models.user import User
from app.models.video import Video
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
        photo = Photo(**kwargs)
        db.add(photo)
        await db.commit()
        await db.refresh(photo)
        return photo


async def _create_video(**kwargs) -> Video:
    async with TestSessionLocal() as db:
        video = Video(**kwargs)
        db.add(video)
        await db.commit()
        await db.refresh(video)
        return video


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
async def uploaded_photo():
    return await _create_photo(
        object_key="photos/existing.jpg", title="Existing", category="Wearable Tech",
        description="", specs=[], status="draft",
    )


@pytest_asyncio.fixture
async def uploaded_video():
    return await _create_video(
        object_key="videos/existing.mp4", title="Existing video", category="Product Demos",
        description="", specs=[], status="draft", duration_seconds=5.0, mime_type="video/mp4",
    )


@pytest.fixture(autouse=True)
def configured_ai(monkeypatch):
    """AI_API_KEY set + generate_media_description mocked -- the default
    for most tests in this file. Tests specifically checking the
    unconfigured-404 path override is_configured() back to False instead
    of using this fixture."""
    import app.core.ai as ai_module
    import app.routers.ai as ai_router_module

    monkeypatch.setattr(ai_module, "is_configured", lambda: True)
    monkeypatch.setattr(ai_router_module.ai_core, "is_configured", lambda: True)

    async def _fake_generate_media_description(*, system_instruction, prompt, media_bytes, mime_type):
        return "TITLE: Sleek Wireless Charger\nDESCRIPTION: A minimalist charging pad with a soft-touch finish.\nSPECS: matte black, compact, rounded edges"

    monkeypatch.setattr(ai_router_module.ai_core, "generate_media_description", _fake_generate_media_description)
    return ai_router_module


@pytest.fixture(autouse=True)
def fake_download(monkeypatch):
    import app.routers.ai as ai_router_module

    def _fake_download_object(object_key: str, bucket=None) -> bytes:
        return b"fake-file-bytes"

    monkeypatch.setattr(ai_router_module, "download_object", _fake_download_object)


async def _admin_client() -> AsyncClient:
    transport = ASGITransport(app=app)
    c = AsyncClient(transport=transport, base_url="http://test")
    resp = await c.post("/api/auth/login", json={"email": "admin@eddyartgallery.app", "password": "super-secret-admin-1"})
    assert resp.status_code == 200, resp.text
    return c


async def _customer_client() -> AsyncClient:
    transport = ASGITransport(app=app)
    c = AsyncClient(transport=transport, base_url="http://test")
    resp = await c.post("/api/customer/login", json={"email": "lena@example.com", "password": "customer-pass-1"})
    assert resp.status_code == 200, resp.text
    return c


async def test_describe_photo_end_to_end(admin_user, uploaded_photo):
    admin = await _admin_client()
    try:
        resp = await admin.post(
            "/api/ai/describe-media", json={"objectKey": uploaded_photo.object_key, "mediaType": "photo"}
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["title"] == "Sleek Wireless Charger"
        assert "minimalist charging pad" in body["description"]
        assert body["specs"] == ["matte black", "compact", "rounded edges"]
    finally:
        await admin.aclose()


async def test_describe_video_end_to_end(admin_user, uploaded_video):
    admin = await _admin_client()
    try:
        resp = await admin.post(
            "/api/ai/describe-media", json={"objectKey": uploaded_video.object_key, "mediaType": "video"}
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["title"] == "Sleek Wireless Charger"
    finally:
        await admin.aclose()


async def test_describe_media_requires_admin_or_staff(customer_user, uploaded_photo):
    customer = await _customer_client()
    try:
        resp = await customer.post(
            "/api/ai/describe-media", json={"objectKey": uploaded_photo.object_key, "mediaType": "photo"}
        )
        assert resp.status_code == 401  # not authenticated as admin/staff at all -- same reasoning as
        # test_videos.py's test_customer_cannot_manage_videos
    finally:
        await customer.aclose()


async def test_describe_media_rejects_objectkey_with_no_matching_upload(admin_user):
    """Prevents this endpoint from being used to fetch-and-describe an
    arbitrary storage path that was never actually uploaded as a real
    Photo/Video -- a made-up objectKey must 404, not silently proceed to
    download_object() and burn a Gemini call on it."""
    admin = await _admin_client()
    try:
        resp = await admin.post(
            "/api/ai/describe-media", json={"objectKey": "photos/never-uploaded.jpg", "mediaType": "photo"}
        )
        assert resp.status_code == 404
    finally:
        await admin.aclose()


async def test_describe_media_404s_when_ai_not_configured(admin_user, uploaded_photo, monkeypatch):
    import app.routers.ai as ai_router_module

    monkeypatch.setattr(ai_router_module.ai_core, "is_configured", lambda: False)

    admin = await _admin_client()
    try:
        resp = await admin.post(
            "/api/ai/describe-media", json={"objectKey": uploaded_photo.object_key, "mediaType": "photo"}
        )
        assert resp.status_code == 404
    finally:
        await admin.aclose()


async def test_describe_media_handles_unparseable_model_response_gracefully(admin_user, uploaded_photo, monkeypatch):
    """Falls back to putting the whole response in `description` if
    Gemini doesn't follow the TITLE:/DESCRIPTION:/SPECS: format exactly --
    an admin still gets something to work with instead of a hard error
    over a model formatting slip."""
    import app.routers.ai as ai_router_module

    async def _fake_freeform(*, system_instruction, prompt, media_bytes, mime_type):
        return "A sleek black charging pad with rounded corners."

    monkeypatch.setattr(ai_router_module.ai_core, "generate_media_description", _fake_freeform)

    admin = await _admin_client()
    try:
        resp = await admin.post(
            "/api/ai/describe-media", json={"objectKey": uploaded_photo.object_key, "mediaType": "photo"}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["title"] == ""
        assert "sleek black charging pad" in body["description"]
        assert body["specs"] == []
    finally:
        await admin.aclose()


async def test_describe_media_returns_503_on_ai_failure(admin_user, uploaded_photo, monkeypatch):
    import app.core.ai as ai_module
    import app.routers.ai as ai_router_module

    async def _raise(*, system_instruction, prompt, media_bytes, mime_type):
        raise ai_module.AIUnavailableError("simulated Gemini outage")

    monkeypatch.setattr(ai_router_module.ai_core, "generate_media_description", _raise)

    admin = await _admin_client()
    try:
        resp = await admin.post(
            "/api/ai/describe-media", json={"objectKey": uploaded_photo.object_key, "mediaType": "photo"}
        )
        assert resp.status_code == 503
    finally:
        await admin.aclose()


async def test_describe_media_rate_limited(admin_user, uploaded_photo, monkeypatch):
    import app.core.config as config_module

    settings = config_module.get_settings()
    monkeypatch.setattr(settings, "AI_RATE_LIMIT_MAX_REQUESTS", 2)

    admin = await _admin_client()
    try:
        for _ in range(2):
            resp = await admin.post(
                "/api/ai/describe-media", json={"objectKey": uploaded_photo.object_key, "mediaType": "photo"}
            )
            assert resp.status_code == 200

        resp = await admin.post(
            "/api/ai/describe-media", json={"objectKey": uploaded_photo.object_key, "mediaType": "photo"}
        )
        assert resp.status_code == 429
    finally:
        await admin.aclose()
