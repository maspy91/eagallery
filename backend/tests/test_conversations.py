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


@pytest_asyncio.fixture
async def staff_user():
    return await _create_user(
        email="staffer@example.com", name="Staffer",
        password_hash=hash_password("staff-pass-1"),
        role="staff", email_verified=True, is_active=True,
    )


async def _login_admin(client, admin_user):
    await client.post("/api/auth/login", json={"email": "admin@eddyartgallery.app", "password": "super-secret-admin-1"})


async def _login_customer(client, customer_user):
    await client.post("/api/customer/login", json={"email": "lena@example.com", "password": "customer-pass-1"})


async def _login_other_customer(client, other_customer):
    await client.post("/api/customer/login", json={"email": "omar@example.com", "password": "customer-pass-2"})


async def _login_staff(client, staff_user):
    await client.post("/api/auth/login", json={"email": "staffer@example.com", "password": "staff-pass-1"})


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
    assert resp.status_code == 401

    resp = await client.post("/api/conversations", json={"subject": "x", "text": "y"})
    conv_id = resp.json()["id"]

    resp = await client.patch(f"/api/conversations/{conv_id}", json={"status": "resolved"})
    assert resp.status_code == 401


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


async def test_conversation_stats_counts_only_non_resolved(client, customer_user, other_customer, admin_user):
    """Regression test for the admin dashboard's old newRequests count,
    which came from conversationsApi.listAll() -- correct but fetches
    every conversation and every message in each one just to filter and
    count client-side. /api/conversations/stats does the count (and the
    status filter) in the database instead."""
    await _login_customer(client, customer_user)
    resp = await client.post("/api/conversations", json={"subject": "Custom signage quote", "text": "Hi"})
    assert resp.status_code == 201, resp.text
    open_conv_id = resp.json()["id"]

    resp = await client.post("/api/conversations", json={"subject": "Award engraving", "text": "Hi again"})
    assert resp.status_code == 201, resp.text
    resolved_conv_id = resp.json()["id"]

    await _login_other_customer(client, other_customer)
    resp = await client.post("/api/conversations", json={"subject": "Bulk order", "text": "Hello"})
    assert resp.status_code == 201, resp.text

    await _login_admin(client, admin_user)
    resp = await client.patch(f"/api/conversations/{resolved_conv_id}", json={"status": "resolved"})
    assert resp.status_code == 200, resp.text

    resp = await client.get("/api/conversations/stats")
    assert resp.status_code == 200, resp.text
    # 3 created total, 1 resolved -- open count should be 2, regardless
    # of which customer they belong to.
    assert resp.json()["openCount"] == 2


async def test_conversation_stats_requires_admin_or_staff(client, customer_user):
    await _login_customer(client, customer_user)
    resp = await client.get("/api/conversations/stats")
    assert resp.status_code == 401


async def test_admin_reply_sends_email_to_customer(client, customer_user, admin_user, captured_emails):
    """Regression test for the previously-missing notification email --
    an admin/staff reply to a business request used to only ever create
    an in-app notification row."""
    await _login_customer(client, customer_user)
    resp = await client.post("/api/conversations", json={"subject": "Custom signage quote", "text": "Hi there"})
    assert resp.status_code == 201, resp.text
    conv_id = resp.json()["id"]
    await client.post("/api/customer/logout")

    await _login_admin(client, admin_user)
    resp = await client.post(f"/api/conversations/{conv_id}/messages", json={"text": "Happy to help with that!"})
    assert resp.status_code == 200, resp.text

    reply_emails = [e for e in captured_emails if e["kind"] == "conversation_reply"]
    assert len(reply_emails) == 1
    assert reply_emails[0]["to"] == "lena@example.com"
    assert reply_emails[0]["sender_name"] == "Admin"
    assert reply_emails[0]["subject"] == "Custom signage quote"
    assert reply_emails[0]["href"] == "/dashboard/inbox"


async def test_customer_reply_to_own_conversation_sends_no_email(client, customer_user, admin_user, captured_emails):
    """Only an admin/staff reply is notification-worthy -- a customer
    replying to their own open thread doesn't need to be told about a
    message they just sent themselves."""
    await _login_customer(client, customer_user)
    resp = await client.post("/api/conversations", json={"subject": "Award engraving", "text": "Hi"})
    conv_id = resp.json()["id"]

    resp = await client.post(f"/api/conversations/{conv_id}/messages", json={"text": "Following up on this"})
    assert resp.status_code == 200, resp.text

    assert [e for e in captured_emails if e["kind"] == "conversation_reply"] == []


async def test_reply_email_uses_current_address_not_stale_creation_snapshot(
    client, customer_user, admin_user, captured_emails
):
    """conversation.customer_email is a snapshot taken when the thread
    was created (see the Conversation model's docstring) and is
    deliberately never kept in sync. If a customer changes their email
    after opening a request, the notification for a later reply must go
    to their CURRENT address, not the stale one captured at creation."""
    await _login_customer(client, customer_user)
    resp = await client.post("/api/conversations", json={"subject": "Bulk order", "text": "Hi"})
    conv_id = resp.json()["id"]

    resp = await client.post(
        "/api/customer/change-email", json={"email": "lena-new@example.com", "currentPassword": "customer-pass-1"}
    )
    assert resp.status_code == 200, resp.text
    await client.post("/api/customer/logout")

    await _login_admin(client, admin_user)
    resp = await client.post(f"/api/conversations/{conv_id}/messages", json={"text": "On it"})
    assert resp.status_code == 200, resp.text

    reply_emails = [e for e in captured_emails if e["kind"] == "conversation_reply"]
    assert len(reply_emails) == 1
    assert reply_emails[0]["to"] == "lena-new@example.com"


# ============================================================
# Quotes -- lightweight, non-payment-processing offers attached to a
# conversation, giving a request a trackable, closeable outcome.
# ============================================================


async def test_create_quote_appears_on_conversation_and_notifies_customer(
    client, customer_user, admin_user, captured_emails
):
    await _login_customer(client, customer_user)
    resp = await client.post("/api/conversations", json={"subject": "Illuminated shop sign", "text": "Hi"})
    conv_id = resp.json()["id"]
    await client.post("/api/customer/logout")

    await _login_admin(client, admin_user)
    resp = await client.post(
        f"/api/conversations/{conv_id}/quotes",
        json={"description": "3 illuminated signs, installation included", "amount": 450000, "currency": "ngn"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body["quotes"]) == 1
    quote = body["quotes"][0]
    assert quote["createdByName"] == "Admin"
    assert quote["description"] == "3 illuminated signs, installation included"
    assert quote["amountCents"] == 45_000_000  # 450000.00 NGN in cents
    assert quote["currency"] == "NGN"  # normalized to uppercase
    assert quote["status"] == "pending"
    assert quote["respondedAt"] is None

    email = [e for e in captured_emails if e["kind"] == "quote"]
    assert len(email) == 1
    assert email[0]["to"] == "lena@example.com"
    assert email[0]["amount_cents"] == 45_000_000


async def test_customer_and_staff_cannot_create_quotes(client, customer_user, staff_user, admin_user):
    await _login_customer(client, customer_user)
    resp = await client.post("/api/conversations", json={"subject": "Bulk order", "text": "Hi"})
    conv_id = resp.json()["id"]

    resp = await client.post(
        f"/api/conversations/{conv_id}/quotes", json={"description": "Self-quote", "amount": 1000}
    )
    assert resp.status_code == 401

    # Staff has requests:respond in this app, same as admin -- confirms
    # quote creation isn't accidentally admin-only.
    await client.post("/api/customer/logout")
    await _login_staff(client, staff_user)
    resp = await client.post(
        f"/api/conversations/{conv_id}/quotes", json={"description": "From staff", "amount": 2000}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["quotes"][-1]["createdByName"] == "Staffer"


async def test_accept_quote_resolves_conversation(client, customer_user, admin_user):
    await _login_customer(client, customer_user)
    resp = await client.post("/api/conversations", json={"subject": "Award engraving", "text": "Hi"})
    conv_id = resp.json()["id"]
    await client.post("/api/customer/logout")

    await _login_admin(client, admin_user)
    resp = await client.post(
        f"/api/conversations/{conv_id}/quotes", json={"description": "50 engraved awards", "amount": 200000}
    )
    quote_id = resp.json()["quotes"][0]["id"]
    assert resp.json()["status"] == "in_progress"  # first admin action on a 'new' thread auto-flips it
    await client.post("/api/auth/logout")

    await _login_customer(client, customer_user)
    resp = await client.post(f"/api/conversations/{conv_id}/quotes/{quote_id}/accept")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["quotes"][0]["status"] == "accepted"
    assert body["quotes"][0]["respondedAt"] is not None
    # The trackable, closeable outcome: accepting a quote resolves the
    # conversation on its own, without staff having to do it manually.
    assert body["status"] == "resolved"


async def test_decline_quote_does_not_resolve_conversation(client, customer_user, admin_user):
    await _login_customer(client, customer_user)
    resp = await client.post("/api/conversations", json={"subject": "Custom trophy", "text": "Hi"})
    conv_id = resp.json()["id"]
    await client.post("/api/customer/logout")

    await _login_admin(client, admin_user)
    resp = await client.post(
        f"/api/conversations/{conv_id}/quotes", json={"description": "1 trophy", "amount": 50000}
    )
    quote_id = resp.json()["quotes"][0]["id"]
    await client.post("/api/auth/logout")

    await _login_customer(client, customer_user)
    resp = await client.post(f"/api/conversations/{conv_id}/quotes/{quote_id}/decline")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["quotes"][0]["status"] == "declined"
    # Declining doesn't close the thread -- staff might send a revised quote.
    assert body["status"] == "in_progress"


async def test_only_owning_customer_can_accept_or_decline(client, customer_user, other_customer, admin_user):
    await _login_customer(client, customer_user)
    resp = await client.post("/api/conversations", json={"subject": "Signage set", "text": "Hi"})
    conv_id = resp.json()["id"]
    await client.post("/api/customer/logout")

    await _login_admin(client, admin_user)
    resp = await client.post(
        f"/api/conversations/{conv_id}/quotes", json={"description": "Full set", "amount": 300000}
    )
    quote_id = resp.json()["quotes"][0]["id"]
    await client.post("/api/auth/logout")

    await _login_other_customer(client, other_customer)
    resp = await client.post(f"/api/conversations/{conv_id}/quotes/{quote_id}/accept")
    assert resp.status_code == 403

    resp = await client.post(f"/api/conversations/{conv_id}/quotes/{quote_id}/decline")
    assert resp.status_code == 403

    # Staff/admin can't accept/decline on the customer's behalf either --
    # get_current_customer rejects any admin/staff session outright.
    await client.post("/api/customer/logout")
    await _login_admin(client, admin_user)
    resp = await client.post(f"/api/conversations/{conv_id}/quotes/{quote_id}/accept")
    assert resp.status_code == 401


async def test_cannot_respond_to_an_already_decided_quote(client, customer_user, admin_user):
    await _login_customer(client, customer_user)
    resp = await client.post("/api/conversations", json={"subject": "Vinyl banner", "text": "Hi"})
    conv_id = resp.json()["id"]
    await client.post("/api/customer/logout")

    await _login_admin(client, admin_user)
    resp = await client.post(
        f"/api/conversations/{conv_id}/quotes", json={"description": "2x3m banner", "amount": 25000}
    )
    quote_id = resp.json()["quotes"][0]["id"]
    await client.post("/api/auth/logout")

    await _login_customer(client, customer_user)
    resp = await client.post(f"/api/conversations/{conv_id}/quotes/{quote_id}/decline")
    assert resp.status_code == 200

    # Can't decline (or accept) it a second time now that it's settled.
    resp = await client.post(f"/api/conversations/{conv_id}/quotes/{quote_id}/decline")
    assert resp.status_code == 409
    resp = await client.post(f"/api/conversations/{conv_id}/quotes/{quote_id}/accept")
    assert resp.status_code == 409


async def test_withdraw_quote(client, customer_user, admin_user, staff_user):
    await _login_customer(client, customer_user)
    resp = await client.post("/api/conversations", json={"subject": "Neon sign", "text": "Hi"})
    conv_id = resp.json()["id"]
    await client.post("/api/customer/logout")

    await _login_admin(client, admin_user)
    resp = await client.post(
        f"/api/conversations/{conv_id}/quotes", json={"description": "Custom neon", "amount": 180000}
    )
    quote_id = resp.json()["quotes"][0]["id"]

    resp = await client.post(f"/api/conversations/{conv_id}/quotes/{quote_id}/withdraw")
    assert resp.status_code == 200, resp.text
    assert resp.json()["quotes"][0]["status"] == "withdrawn"

    # Withdrawn is also a settled state -- can't then be accepted.
    await client.post("/api/auth/logout")
    await _login_customer(client, customer_user)
    resp = await client.post(f"/api/conversations/{conv_id}/quotes/{quote_id}/accept")
    assert resp.status_code == 409


async def test_customer_cannot_withdraw_a_quote(client, customer_user, admin_user):
    await _login_customer(client, customer_user)
    resp = await client.post("/api/conversations", json={"subject": "Poster prints", "text": "Hi"})
    conv_id = resp.json()["id"]
    await client.post("/api/customer/logout")

    await _login_admin(client, admin_user)
    resp = await client.post(
        f"/api/conversations/{conv_id}/quotes", json={"description": "100 posters", "amount": 15000}
    )
    quote_id = resp.json()["quotes"][0]["id"]
    await client.post("/api/auth/logout")

    await _login_customer(client, customer_user)
    resp = await client.post(f"/api/conversations/{conv_id}/quotes/{quote_id}/withdraw")
    assert resp.status_code == 401


async def test_quote_for_nonexistent_conversation_or_quote_returns_404(client, customer_user, admin_user):
    await _login_customer(client, customer_user)
    resp = await client.post("/api/conversations", json={"subject": "Real one", "text": "Hi"})
    conv_id = resp.json()["id"]
    await client.post("/api/customer/logout")

    await _login_admin(client, admin_user)
    resp = await client.post(
        "/api/conversations/does-not-exist/quotes", json={"description": "x", "amount": 100}
    )
    assert resp.status_code == 404

    resp = await client.post(
        f"/api/conversations/{conv_id}/quotes/does-not-exist/withdraw"
    )
    assert resp.status_code == 404


# ============================================================
# Search, date-range filtering, and CSV export
# ============================================================


async def test_conversation_search_matches_subject_name_or_email(client, customer_user, other_customer, admin_user):
    await _login_customer(client, customer_user)
    resp = await client.post("/api/conversations", json={"subject": "Illuminated shop sign", "text": "Hi"})
    assert resp.status_code == 201, resp.text
    await client.post("/api/customer/logout")

    await _login_other_customer(client, other_customer)
    resp = await client.post("/api/conversations", json={"subject": "Bulk trophy order", "text": "Hi"})
    assert resp.status_code == 201, resp.text
    await client.post("/api/customer/logout")

    await _login_admin(client, admin_user)
    resp = await client.get("/api/conversations", params={"q": "illuminated"})
    assert resp.status_code == 200, resp.text
    assert [c["subject"] for c in resp.json()] == ["Illuminated shop sign"]

    # Matches by customer name too (other_customer is "Omar Haddad").
    resp = await client.get("/api/conversations", params={"q": "omar"})
    assert resp.status_code == 200, resp.text
    assert [c["subject"] for c in resp.json()] == ["Bulk trophy order"]

    # And by email.
    resp = await client.get("/api/conversations", params={"q": "lena@example.com"})
    assert resp.status_code == 200, resp.text
    assert [c["subject"] for c in resp.json()] == ["Illuminated shop sign"]


async def test_conversation_date_range_filters_by_created_at(client, customer_user, admin_user):
    from datetime import datetime, timedelta, timezone
    from app.models.conversation import Conversation

    await _login_customer(client, customer_user)
    resp = await client.post("/api/conversations", json={"subject": "Old request", "text": "Hi"})
    old_id = resp.json()["id"]
    resp = await client.post("/api/conversations", json={"subject": "New request", "text": "Hi"})
    assert resp.status_code == 201, resp.text

    async with TestSessionLocal() as db:
        conv = await db.get(Conversation, old_id)
        conv.created_at = datetime.now(timezone.utc) - timedelta(days=30)
        await db.commit()

    await _login_admin(client, admin_user)
    today = datetime.now(timezone.utc).date().isoformat()
    resp = await client.get("/api/conversations", params={"date_from": today})
    assert resp.status_code == 200, resp.text
    subjects = [c["subject"] for c in resp.json()]
    assert "New request" in subjects
    assert "Old request" not in subjects


async def test_conversation_export_csv_matches_filters_and_requires_respond_permission(
    client, customer_user, admin_user
):
    await _login_customer(client, customer_user)
    resp = await client.post("/api/conversations", json={"subject": "Exportable request", "text": "Hi"})
    assert resp.status_code == 201, resp.text
    await client.post("/api/customer/logout")

    await _login_admin(client, admin_user)
    resp = await client.get("/api/conversations/export")
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("text/csv")
    assert "attachment" in resp.headers["content-disposition"]
    body = resp.text
    assert "Exportable request" in body
    assert "lena@example.com" in body
    assert body.startswith("ID,Subject,Customer Name,Customer Email,Status,Created At,Updated At")

    await client.post("/api/auth/logout")
    await _login_customer(client, customer_user)
    resp = await client.get("/api/conversations/export")
    assert resp.status_code == 401
