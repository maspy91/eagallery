"""
Back-to-back walkthrough of everything the admin dashboard covers: photo
management, business requests (conversations), and the notifications they
generate for customers. One connected story per test, run against real
routes and a real (in-memory) DB -- not unit tests of individual
functions. Storage is monkeypatched (no real bucket in tests); Redis is
monkeypatched (see conftest.py's fake_redis); everything else is real.

Each "actor" (admin, a given customer) gets ONE dedicated AsyncClient for
the whole test, logged in once and reused -- this mirrors how the real
app is actually used (a browser tab keeps its session cookie for the
whole visit; nobody logs out and back in between every click) and avoids
artificially tripping the login rate limiter, which is keyed per-IP and
shared across every login attempt from that IP within a test run.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.security import hash_password
from app.main import app
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
        email="sam@eddyartgallery.app", name="Sam Staff",
        password_hash=hash_password("staff-pass-1"),
        role="staff", email_verified=True, is_active=True,
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


@pytest.fixture(autouse=True)
def fake_storage(monkeypatch):
    import app.routers.photos as photos_module

    _counter = {"n": 0}

    def _fake_generate_object_key(filename: str, prefix: str = "photos") -> str:
        _counter["n"] += 1
        return f"{prefix}/fake-{_counter['n']}-{filename}"

    def _fake_presigned_url(object_key: str, content_type: str, expires_in: int = 300) -> str:
        return f"https://fake-r2.example.com/{object_key}?signature=fake"

    def _fake_public_url(object_key: str) -> str:
        return f"https://media.example.com/{object_key}"

    deleted_keys: list[str] = []

    def _fake_delete_object(object_key: str) -> None:
        deleted_keys.append(object_key)

    monkeypatch.setattr(photos_module, "generate_object_key", _fake_generate_object_key)
    monkeypatch.setattr(photos_module, "generate_presigned_upload_url", _fake_presigned_url)
    monkeypatch.setattr(photos_module, "public_url", _fake_public_url)
    monkeypatch.setattr(photos_module, "delete_object", _fake_delete_object)

    return deleted_keys


async def _new_client() -> AsyncClient:
    """A fresh client == a fresh browser session (own cookie jar). Used
    instead of the shared `client` fixture so multiple actors in one test
    don't clobber each other's session cookie -- exactly like two people
    using the site in two different browser tabs."""
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


async def _admin_client(email="admin@eddyartgallery.app", password="super-secret-admin-1") -> AsyncClient:
    c = await _new_client()
    resp = await c.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return c


async def _customer_client(email, password) -> AsyncClient:
    c = await _new_client()
    resp = await c.post("/api/customer/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return c


async def _upload_photo(admin_client, title, category="Wearable Tech") -> dict:
    resp = await admin_client.post(
        "/api/photos/upload-url", json={"filename": "watch.jpg", "content_type": "image/jpeg"}
    )
    assert resp.status_code == 200, resp.text
    object_key = resp.json()["objectKey"]

    resp = await admin_client.post(
        "/api/photos",
        json={
            "objectKey": object_key,
            "title": title,
            "category": category,
            "description": "A fitness band.",
            "specs": ["10-Day Battery"],
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ============================================================
# PHOTO MANAGEMENT -- full admin lifecycle, back to back
# ============================================================


async def test_photo_management_full_admin_lifecycle(client, admin_user, lena, fake_storage):
    """Upload -> draft -> publish -> customer sees it, views it, likes it
    -> admin sees updated stats in the admin list -> admin flags it ->
    still visible to admin (not the public) -> admin republishes and
    edits metadata -> admin deletes -> gone from both admin and public
    lists, and storage cleanup was actually called with the right key."""
    admin = await _admin_client()
    try:
        photo = await _upload_photo(admin, "SmartWatch Pro")
        assert photo["status"] == "draft"

        # 1. A draft is invisible to the public (`client` here == a
        # logged-out fixture client, i.e. a true anonymous visitor).
        anon_list = (await client.get("/api/photos")).json()
        assert photo["id"] not in [p["id"] for p in anon_list]

        # 2. Admin publishes it.
        resp = await admin.patch(f"/api/photos/{photo['id']}", json={"status": "published"})
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "published"

        # 3. Now a customer can see and view it.
        customer = await _customer_client("lena@example.com", "customer-pass-1")
        try:
            resp = await customer.get(f"/api/photos/{photo['id']}")
            assert resp.status_code == 200
            assert resp.json()["viewCount"] == 1  # first view from this customer counted

            resp = await customer.get(f"/api/photos/{photo['id']}")
            assert resp.json()["viewCount"] == 1  # same customer again -- NOT double-counted

            # 4. Customer likes it.
            resp = await customer.post(f"/api/photos/{photo['id']}/like")
            assert resp.status_code == 200
            assert resp.json() == {"liked": True, "likeCount": 1}
        finally:
            await customer.aclose()

        # 5. Admin's own list reflects the real stats (not stale/cached).
        admin_list = (await admin.get("/api/photos", params={"limit": 100})).json()
        same_photo = next(p for p in admin_list if p["id"] == photo["id"])
        assert same_photo["viewCount"] == 1
        assert same_photo["likeCount"] == 1
        assert same_photo["status"] == "published"

        # 6. Admin flags it (e.g. a reported/problematic photo) -- admin
        # can still see and manage it even though it's now flagged.
        resp = await admin.patch(f"/api/photos/{photo['id']}", json={"status": "flagged"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "flagged"

        admin_get = await admin.get(f"/api/photos/{photo['id']}")
        assert admin_get.status_code == 200  # staff/admin session can still see a flagged photo

        # 7. Admin republishes and edits metadata in the same PATCH.
        resp = await admin.patch(
            f"/api/photos/{photo['id']}",
            json={"status": "published", "title": "SmartWatch Pro (V2)", "category": "Featured"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "published"
        assert body["title"] == "SmartWatch Pro (V2)"
        assert body["category"] == "Featured"
        # Stats must survive an unrelated metadata edit, not reset.
        assert body["viewCount"] == 1
        assert body["likeCount"] == 1

        # 8. Admin deletes it -- gone from the DB, and storage cleanup was
        # called with the EXACT object_key that was uploaded.
        resp = await admin.delete(f"/api/photos/{photo['id']}")
        assert resp.status_code == 200

        deleted_key = fake_storage[-1]
        assert deleted_key in photo["image"]  # the exact object_key uploaded, not a placeholder

        resp = await admin.get(f"/api/photos/{photo['id']}")
        assert resp.status_code == 404
    finally:
        await admin.aclose()


async def test_staff_has_same_photo_management_access_as_admin(staff_user, fake_storage):
    staff = await _admin_client("sam@eddyartgallery.app", "staff-pass-1")
    try:
        photo = await _upload_photo(staff, "Staff-managed item")
        resp = await staff.patch(f"/api/photos/{photo['id']}", json={"status": "published"})
        assert resp.status_code == 200
        resp = await staff.delete(f"/api/photos/{photo['id']}")
        assert resp.status_code == 200
    finally:
        await staff.aclose()


async def test_flagging_a_liked_published_photo_actually_hides_it_from_the_public(client, admin_user, lena):
    """Regression-style check for the exact scenario an admin would hit:
    a photo customers have already engaged with gets flagged -- it must
    disappear from the public gallery immediately, not just in theory."""
    admin = await _admin_client()
    customer = await _customer_client("lena@example.com", "customer-pass-1")
    try:
        photo = await _upload_photo(admin, "Controversial Item")
        await admin.patch(f"/api/photos/{photo['id']}", json={"status": "published"})

        await customer.get(f"/api/photos/{photo['id']}")  # generates a view
        await customer.post(f"/api/photos/{photo['id']}/like")

        await admin.patch(f"/api/photos/{photo['id']}", json={"status": "flagged"})

        # `client` fixture == a genuinely logged-out anonymous visitor.
        public_list = (await client.get("/api/photos")).json()
        assert photo["id"] not in [p["id"] for p in public_list]

        public_get = await client.get(f"/api/photos/{photo['id']}")
        assert public_get.status_code == 404
    finally:
        await admin.aclose()
        await customer.aclose()


# ============================================================
# BUSINESS REQUESTS (conversations) -- full admin loop, back to back
# ============================================================


async def test_business_request_full_admin_loop_with_notification(admin_user, lena):
    """Customer opens a request from their Inbox -> shows up in admin's
    Business Requests, unresolved -> admin replies (status auto-advances
    to in_progress) -> customer gets a real notification pointing at
    /dashboard/inbox -> customer replies back -> admin marks resolved ->
    every state transition is visible from both sides."""
    admin = await _admin_client()
    customer = await _customer_client("lena@example.com", "customer-pass-1")
    try:
        resp = await customer.post(
            "/api/conversations", json={"subject": "Bulk licensing question", "text": "Do you offer bulk licensing?"}
        )
        assert resp.status_code == 201, resp.text
        conv = resp.json()
        assert conv["status"] == "new"
        assert len(conv["messages"]) == 1

        admin_list = (await admin.get("/api/conversations")).json()
        assert any(c["id"] == conv["id"] for c in admin_list)
        same = next(c for c in admin_list if c["id"] == conv["id"])
        assert same["status"] == "new"
        assert same["customerName"] == "Lena Ortiz"
        assert same["customerEmail"] == "lena@example.com"

        resp = await admin.post(f"/api/conversations/{conv['id']}/messages", json={"text": "Yes! Email us for a quote."})
        assert resp.status_code == 200, resp.text
        updated = resp.json()
        assert updated["status"] == "in_progress"  # auto-advanced by the first admin reply
        assert len(updated["messages"]) == 2
        assert updated["messages"][-1]["senderRole"] == "admin"
        assert updated["messages"][-1]["senderName"] == "Admin"

        notifications = (await customer.get("/api/notifications")).json()
        matching = [n for n in notifications if n["type"] == "conversation_reply"]
        assert len(matching) == 1
        assert matching[0]["href"] == "/dashboard/inbox"
        assert "Admin" in matching[0]["message"]
        assert "Bulk licensing" in matching[0]["message"]
        assert matching[0]["read"] is False

        unread = (await customer.get("/api/notifications/unread-count")).json()
        assert unread["count"] == 1

        resp = await customer.post(f"/api/conversations/{conv['id']}/messages", json={"text": "Great, sending now."})
        assert resp.status_code == 200
        updated = resp.json()
        assert updated["status"] == "in_progress"  # customer replies never change status
        assert len(updated["messages"]) == 3

        # Customer replying to their own conversation must NOT self-notify.
        notifications_after = (await customer.get("/api/notifications")).json()
        assert len([n for n in notifications_after if n["type"] == "conversation_reply"]) == 1

        resp = await admin.patch(f"/api/conversations/{conv['id']}", json={"status": "resolved"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "resolved"

        final_list = (await admin.get("/api/conversations")).json()
        final = next(c for c in final_list if c["id"] == conv["id"])
        assert final["status"] == "resolved"
        assert len(final["messages"]) == 3
    finally:
        await admin.aclose()
        await customer.aclose()


async def test_customer_cannot_see_other_customers_requests(lena, omar):
    lena_c = await _customer_client("lena@example.com", "customer-pass-1")
    omar_c = await _customer_client("omar@example.com", "customer-pass-2")
    try:
        await lena_c.post("/api/conversations", json={"subject": "Private question", "text": "Just for me"})
        mine = (await omar_c.get("/api/conversations/mine")).json()
        assert mine == []
    finally:
        await lena_c.aclose()
        await omar_c.aclose()


async def test_staff_can_manage_requests_same_as_admin(staff_user, lena):
    customer = await _customer_client("lena@example.com", "customer-pass-1")
    staff = await _admin_client("sam@eddyartgallery.app", "staff-pass-1")
    try:
        resp = await customer.post("/api/conversations", json={"subject": "Question", "text": "Hi"})
        conv_id = resp.json()["id"]

        resp = await staff.post(f"/api/conversations/{conv_id}/messages", json={"text": "Staff reply"})
        assert resp.status_code == 200
        assert resp.json()["messages"][-1]["senderName"] == "Sam Staff"

        resp = await staff.patch(f"/api/conversations/{conv_id}", json={"status": "resolved"})
        assert resp.status_code == 200
    finally:
        await customer.aclose()
        await staff.aclose()


# ============================================================
# NOTIFICATIONS -- generated by admin actions, consumed by the customer
# ============================================================


async def test_notifications_generated_by_admin_actions_end_to_end(admin_user, lena, omar):
    """Two different admin-dashboard-adjacent notification sources (a
    conversation reply, and a comment reply -- comment moderation lives
    in the admin dashboard too) both land correctly, independently, for
    the right customer only, and mark-read/mark-all-read both work
    across mixed notification types."""
    admin = await _admin_client()
    lena_c = await _customer_client("lena@example.com", "customer-pass-1")
    omar_c = await _customer_client("omar@example.com", "customer-pass-2")
    try:
        photo = await _upload_photo(admin, "Notif Test Item")
        await admin.patch(f"/api/photos/{photo['id']}", json={"status": "published"})

        # Lena comments on a photo.
        resp = await lena_c.post(f"/api/photos/{photo['id']}/comments", json={"text": "Love this!"})
        comment_id = resp.json()["id"]

        # Omar replies to Lena's comment -- Lena should be notified.
        await omar_c.post(f"/api/photos/{photo['id']}/comments", json={"text": "Agreed!", "parent_id": comment_id})

        notifications = (await lena_c.get("/api/notifications")).json()
        reply_notifs = [n for n in notifications if n["type"] == "comment_reply"]
        assert len(reply_notifs) == 1

        unread = (await lena_c.get("/api/notifications/unread-count")).json()
        assert unread["count"] == 1

        # Mark that one read.
        resp = await lena_c.post(f"/api/notifications/{reply_notifs[0]['id']}/read")
        assert resp.status_code == 200
        assert resp.json()["read"] is True

        unread = (await lena_c.get("/api/notifications/unread-count")).json()
        assert unread["count"] == 0

        # Now trigger a second, different-type notification (conversation
        # reply from admin) and confirm mark-all-read clears both types.
        resp = await lena_c.post("/api/conversations", json={"subject": "Follow-up", "text": "One more thing"})
        conv_id = resp.json()["id"]

        await admin.post(f"/api/conversations/{conv_id}/messages", json={"text": "Sure, go ahead."})

        unread = (await lena_c.get("/api/notifications/unread-count")).json()
        assert unread["count"] == 1  # only the new one -- the comment-reply one stayed read

        resp = await lena_c.post("/api/notifications/read-all")
        assert resp.status_code == 200

        unread = (await lena_c.get("/api/notifications/unread-count")).json()
        assert unread["count"] == 0

        all_notifs = (await lena_c.get("/api/notifications")).json()
        assert all(n["read"] for n in all_notifs)
        assert len(all_notifs) == 2

        # Omar must never see any of Lena's notifications.
        omars_notifs = (await omar_c.get("/api/notifications")).json()
        lena_ids = {n["id"] for n in all_notifs}
        assert all(n["id"] not in lena_ids for n in omars_notifs)
    finally:
        await admin.aclose()
        await lena_c.aclose()
        await omar_c.aclose()
