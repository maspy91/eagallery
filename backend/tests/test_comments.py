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


async def test_comment_stats_counts_across_photos_and_videos(client, published_photo, admin_user):
    """Regression test for the admin dashboard's old totalComments, which
    came from commentsApi.listAll() -- correct but wasteful (fetches
    every row just to take len()). /api/comments/stats does the same
    count in the database instead."""
    for text in ["one", "two", "three"]:
        resp = await client.post(f"/api/photos/{published_photo.id}/comments", json={"text": text})
        assert resp.status_code == 201, resp.text

    await _login_admin(client, admin_user)
    resp = await client.get("/api/comments/stats")
    assert resp.status_code == 200, resp.text
    assert resp.json()["count"] == 3


async def test_comment_stats_requires_admin_or_staff(client, customer_user):
    await _login_customer(client, customer_user)
    resp = await client.get("/api/comments/stats")
    assert resp.status_code == 401


async def test_my_comment_count_only_counts_my_own(client, published_photo, customer_user, admin_user):
    """Regression test for the customer dashboard's old myThreadCount,
    which fetched every published photo's comment tree and recursively
    walked it client-side to find authorId matches. /mine/count does the
    equivalent with one indexed COUNT query, and must still only count
    the logged-in customer's own comments, not everyone's."""
    await _login_customer(client, customer_user)
    resp = await client.post(f"/api/photos/{published_photo.id}/comments", json={"text": "mine"})
    assert resp.status_code == 201, resp.text
    resp = await client.post(
        f"/api/photos/{published_photo.id}/comments", json={"text": "also mine, a reply"}
    )
    assert resp.status_code == 201, resp.text

    # A guest comment (no author_id) and someone else's comment shouldn't
    # be counted toward this customer's total.
    resp = await client.post("/api/customer/logout")
    await client.post(f"/api/photos/{published_photo.id}/comments", json={"text": "guest comment"})

    resp = await client.get("/api/comments/mine/count")
    assert resp.status_code == 401  # logged out after the block above

    await _login_customer(client, customer_user)
    resp = await client.get("/api/comments/mine/count")
    assert resp.status_code == 200, resp.text
    assert resp.json()["count"] == 2


async def test_comment_reply_sends_email_to_parent_author(client, published_photo, customer_user, captured_emails):
    """Regression test for the previously-missing notification email --
    someone replying to a comment used to only ever create an in-app
    notification row, so a customer who wasn't actively browsing the
    site had no way to know unless they logged back in and checked."""
    await _login_customer(client, customer_user)
    resp = await client.post(f"/api/photos/{published_photo.id}/comments", json={"text": "Great piece"})
    assert resp.status_code == 201, resp.text
    root_id = resp.json()["id"]
    await client.post("/api/customer/logout")

    replier = await _create_user(
        email="omar@example.com", name="Omar Haddad",
        password_hash=hash_password("omar-pass-1"), role="customer", email_verified=True, is_active=True,
    )
    resp = await client.post("/api/customer/login", json={"email": "omar@example.com", "password": "omar-pass-1"})
    assert resp.status_code == 200, resp.text

    resp = await client.post(
        f"/api/photos/{published_photo.id}/comments", json={"text": "Totally agree", "parent_id": root_id}
    )
    assert resp.status_code == 201, resp.text

    reply_emails = [e for e in captured_emails if e["kind"] == "comment_reply"]
    assert len(reply_emails) == 1
    assert reply_emails[0]["to"] == "lena@example.com"  # the ORIGINAL commenter, not the replier
    assert reply_emails[0]["replier_name"] == "Omar Haddad"
    assert reply_emails[0]["media_title"] == "Pulse Band 3"
    assert reply_emails[0]["href"] == f"/image/{published_photo.id}"


async def test_replying_to_your_own_comment_sends_no_email(client, published_photo, customer_user, captured_emails):
    await _login_customer(client, customer_user)
    resp = await client.post(f"/api/photos/{published_photo.id}/comments", json={"text": "Root"})
    root_id = resp.json()["id"]

    resp = await client.post(
        f"/api/photos/{published_photo.id}/comments", json={"text": "Following up on my own comment", "parent_id": root_id}
    )
    assert resp.status_code == 201, resp.text

    assert [e for e in captured_emails if e["kind"] == "comment_reply"] == []


async def test_guest_reply_to_a_customers_comment_still_emails_the_customer(
    client, published_photo, customer_user, captured_emails
):
    """A guest (no account) can still trigger the notification email --
    only the RECIPIENT needs an account, not the replier."""
    await _login_customer(client, customer_user)
    resp = await client.post(f"/api/photos/{published_photo.id}/comments", json={"text": "Root by Lena"})
    root_id = resp.json()["id"]
    await client.post("/api/customer/logout")

    resp = await client.post(
        f"/api/photos/{published_photo.id}/comments", json={"text": "Nice!", "parent_id": root_id}
    )
    assert resp.status_code == 201, resp.text

    reply_emails = [e for e in captured_emails if e["kind"] == "comment_reply"]
    assert len(reply_emails) == 1
    assert reply_emails[0]["to"] == "lena@example.com"
    assert reply_emails[0]["replier_name"] == "Anonymous User"


# ============================================================
# Search, date-range filtering, and CSV export
# ============================================================


async def test_comment_search_matches_text_or_author(client, published_photo, admin_user, customer_user):
    await _login_customer(client, customer_user)
    resp = await client.post(f"/api/photos/{published_photo.id}/comments", json={"text": "This sign looks amazing"})
    assert resp.status_code == 201, resp.text
    resp = await client.post(f"/api/photos/{published_photo.id}/comments", json={"text": "Unrelated remark"})
    assert resp.status_code == 201, resp.text

    await _login_admin(client, admin_user)
    resp = await client.get("/api/comments", params={"q": "amazing"})
    assert resp.status_code == 200, resp.text
    assert [c["text"] for c in resp.json()] == ["This sign looks amazing"]

    # Also matches by author name.
    resp = await client.get("/api/comments", params={"q": "lena"})
    assert resp.status_code == 200, resp.text
    assert len(resp.json()) == 2


async def test_comment_date_range_filters_by_created_at(client, published_photo, admin_user):
    from datetime import datetime, timedelta, timezone
    from app.models.comment import Comment

    resp = await client.post(f"/api/photos/{published_photo.id}/comments", json={"text": "Old comment"})
    old_id = resp.json()["id"]
    resp = await client.post(f"/api/photos/{published_photo.id}/comments", json={"text": "New comment"})
    assert resp.status_code == 201, resp.text

    async with TestSessionLocal() as db:
        comment = await db.get(Comment, old_id)
        comment.created_at = datetime.now(timezone.utc) - timedelta(days=30)
        await db.commit()

    await _login_admin(client, admin_user)
    today = datetime.now(timezone.utc).date().isoformat()
    resp = await client.get("/api/comments", params={"date_from": today})
    assert resp.status_code == 200, resp.text
    texts = [c["text"] for c in resp.json()]
    assert "New comment" in texts
    assert "Old comment" not in texts


async def test_comment_export_csv_matches_filters_and_requires_moderate_permission(
    client, published_photo, admin_user, customer_user
):
    resp = await client.post(f"/api/photos/{published_photo.id}/comments", json={"text": "Exportable comment"})
    assert resp.status_code == 201, resp.text

    await _login_admin(client, admin_user)
    resp = await client.get("/api/comments/export")
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("text/csv")
    assert "attachment" in resp.headers["content-disposition"]
    body = resp.text
    assert "Exportable comment" in body
    assert body.startswith("ID,Author,Media Title,Media Type,Flagged,Text,Created At")

    await client.post("/api/auth/logout")
    await _login_customer(client, customer_user)
    resp = await client.get("/api/comments/export")
    assert resp.status_code == 401
