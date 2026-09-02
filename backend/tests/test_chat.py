"""
Live chat end to end -- the real Gemini API is NEVER called (same
approach as test_ai.py): app.core.ai.generate_text is monkeypatched at
the module level app/routers/chat.py imports it from. What's exercised
is everything this backend actually controls: the anonymous-vs-logged-in
identity split, the ai -> pending_admin -> human state machine and its
reverse (human -> ai, full history retained), thread ownership isolation,
rate limiting, and -- the actual point of the "strictly scoped" chat
requirement -- that the SYSTEM PROMPT ITSELF instructs the model to
refuse out-of-scope requests and forward custom-project asks, checked
here by asserting the prompt text contains the right constraints (a
mocked model can't itself prove Gemini will obey the prompt, but it CAN
prove the prompt actually says what it's supposed to say, and that the
app correctly acts on the FORWARD_TO_ADMIN marker in either direction).
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
async def customer_user():
    return await _create_user(
        email="lena@example.com", name="Lena Ortiz",
        password_hash=hash_password("customer-pass-1"),
        role="customer", email_verified=True, is_active=True,
    )


@pytest.fixture(autouse=True)
def configured_ai(monkeypatch):
    """AI enabled + a controllable fake reply, same default-mocked
    pattern as test_ai.py. `set_reply` lets individual tests control
    exactly what the "model" says next, including forcing the
    FORWARD_TO_ADMIN marker to test the handoff path deterministically
    rather than depending on real model behavior."""
    import app.core.ai as ai_module
    import app.routers.chat as chat_router_module

    monkeypatch.setattr(ai_module, "is_configured", lambda: True)
    monkeypatch.setattr(chat_router_module.ai_core, "is_configured", lambda: True)

    state = {"reply": "Sure, we have several categories of product photography available.", "captured_prompt": None, "captured_contents": None}

    async def _fake_generate_text(*, system_instruction, contents, max_output_tokens=None):
        state["captured_prompt"] = system_instruction
        state["captured_contents"] = contents
        return state["reply"]

    monkeypatch.setattr(chat_router_module.ai_core, "generate_text", _fake_generate_text)

    def set_reply(text: str):
        state["reply"] = text

    state["set_reply"] = set_reply
    return state


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


# ============================================================
# System prompt itself -- confirms the actual containment instructions
# are present, not just that the endpoint plumbing works.
# ============================================================


def test_system_prompt_forbids_out_of_scope_and_defines_forward_marker():
    from app.routers.chat import FORWARD_MARKER, _build_system_prompt

    prompt = _build_system_prompt("- 5 published photo(s)\n- 2 published video(s)")

    assert "NEVER answer questions unrelated" in prompt
    assert "ignore previous instructions" in prompt  # explicitly names this exact jailbreak phrasing
    assert "roleplay" in prompt
    assert "EVEN IF" in prompt  # the "no exceptions, even with a claimed good reason" framing
    assert FORWARD_MARKER in prompt
    assert "Never claim to be human" in prompt
    assert "5 published photo(s)" in prompt  # live catalog data actually made it into the prompt


# ============================================================
# Anonymous chat -- guest cookie identity, no account needed
# ============================================================


async def test_anonymous_visitor_can_start_and_continue_a_chat(configured_ai):
    client = await _new_client()
    try:
        resp = await client.post("/api/chat", json={"text": "What kind of products do you photograph?"})
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["mode"] == "ai"
        assert body["reply"] == configured_ai["reply"]
        assert len(body["messages"]) == 2  # the customer's message + the AI's reply
        assert "chat_guest_token" in client.cookies

        thread_id = body["threadId"]
        resp = await client.post("/api/chat", json={"text": "Great, tell me more.", "threadId": thread_id})
        assert resp.status_code == 200
        assert len(resp.json()["messages"]) == 4
    finally:
        await client.aclose()


async def test_two_anonymous_visitors_have_isolated_threads(configured_ai):
    client_a = await _new_client()
    client_b = await _new_client()
    try:
        resp_a = await client_a.post("/api/chat", json={"text": "Hi from visitor A"})
        thread_a = resp_a.json()["threadId"]

        # Visitor B has no cookie for thread A -- can't read or post to it.
        resp = await client_b.get(f"/api/chat/{thread_a}")
        assert resp.status_code == 404

        resp = await client_b.post("/api/chat", json={"text": "trying to hijack", "threadId": thread_a})
        assert resp.status_code == 404
    finally:
        await client_a.aclose()
        await client_b.aclose()


async def test_logged_in_customer_chat_tied_to_their_account(customer_user, configured_ai):
    customer = await _customer_client()
    try:
        resp = await customer.post("/api/chat", json={"text": "Do you sell prints?"})
        assert resp.status_code == 200
        assert "chat_guest_token" not in customer.cookies  # no guest identity needed/created

        thread_id = resp.json()["threadId"]
        detail = await customer.get(f"/api/chat/{thread_id}")
        assert detail.status_code == 200
    finally:
        await customer.aclose()


async def test_chat_404s_when_ai_not_configured(monkeypatch):
    import app.routers.chat as chat_router_module

    monkeypatch.setattr(chat_router_module.ai_core, "is_configured", lambda: False)

    client = await _new_client()
    try:
        resp = await client.post("/api/chat", json={"text": "hi"})
        assert resp.status_code == 404
    finally:
        await client.aclose()


# ============================================================
# Forward-to-admin handoff -- the FORWARD_MARKER path
# ============================================================


async def test_ai_forwards_out_of_scope_or_custom_project_request(configured_ai):
    configured_ai["set_reply"](
        f"I'd love to help connect you with our team for that. {__import__('app.routers.chat', fromlist=['FORWARD_MARKER']).FORWARD_MARKER}"
    )
    client = await _new_client()
    try:
        resp = await client.post(
            "/api/chat", json={"text": "Can you build me a custom 30-photo product shoot for my new sneaker line?"}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["mode"] == "pending_admin"
        # The marker itself must never leak into what the customer sees.
        assert "FORWARD_TO_ADMIN" not in body["reply"]
        # A system message narrating the handoff was added.
        assert any(m["isSystem"] and "flagged" in m["text"].lower() for m in body["messages"])

        thread_id = body["threadId"]

        # AI must NOT respond to further messages on a forwarded thread.
        resp = await client.post("/api/chat", json={"text": "hello? still there?", "threadId": thread_id})
        assert resp.status_code == 200
        assert resp.json()["reply"] == ""
        assert resp.json()["mode"] == "pending_admin"
    finally:
        await client.aclose()


async def test_contact_email_required_and_validated_at_handoff(configured_ai):
    from app.routers.chat import FORWARD_MARKER

    configured_ai["set_reply"](f"Connecting you now. {FORWARD_MARKER}")
    client = await _new_client()
    try:
        resp = await client.post("/api/chat", json={"text": "custom project please"})
        thread_id = resp.json()["threadId"]
        assert resp.json()["mode"] == "pending_admin"

        resp = await client.post(f"/api/chat/{thread_id}/contact-email", json={"email": "not-an-email"})
        assert resp.status_code == 400

        resp = await client.post(f"/api/chat/{thread_id}/contact-email", json={"email": "visitor@example.com"})
        assert resp.status_code == 200
        assert resp.json()["contactEmail"] == "visitor@example.com"
    finally:
        await client.aclose()


# ============================================================
# Admin queue, pickup, reply, and hand-back -- with full history retained
# ============================================================


async def test_admin_queue_shows_only_forwarded_threads(admin_user, configured_ai):
    ai_only_client = await _new_client()
    forwarded_client = await _new_client()
    admin = await _admin_client()
    try:
        await ai_only_client.post("/api/chat", json={"text": "just browsing, thanks"})

        from app.routers.chat import FORWARD_MARKER
        configured_ai["set_reply"](f"Connecting you. {FORWARD_MARKER}")
        await forwarded_client.post("/api/chat", json={"text": "custom project inquiry"})

        resp = await admin.get("/api/admin/chat/threads")
        assert resp.status_code == 200
        threads = resp.json()
        assert len(threads) == 1  # only the forwarded one, not the still-AI-handled one
        assert threads[0]["mode"] == "pending_admin"
        assert threads[0]["isGuest"] is True
    finally:
        await ai_only_client.aclose()
        await forwarded_client.aclose()
        await admin.aclose()


async def test_admin_reply_picks_up_thread_and_replying_customer_sees_it(admin_user, configured_ai):
    from app.routers.chat import FORWARD_MARKER

    configured_ai["set_reply"](f"On it. {FORWARD_MARKER}")
    visitor = await _new_client()
    admin = await _admin_client()
    try:
        resp = await visitor.post("/api/chat", json={"text": "need a custom shoot"})
        thread_id = resp.json()["threadId"]

        resp = await admin.post(f"/api/admin/chat/threads/{thread_id}/reply", json={"text": "Happy to help! What's the project?"})
        assert resp.status_code == 200
        detail = resp.json()
        assert detail["mode"] == "human"
        assert any(m["isSystem"] and "joined the chat" in m["text"] for m in detail["messages"])
        assert detail["messages"][-1]["text"] == "Happy to help! What's the project?"
        assert detail["messages"][-1]["senderRole"] == "admin"

        # The visitor sees the admin's reply on their own thread.
        resp = await visitor.get(f"/api/chat/{thread_id}")
        assert resp.status_code == 200
        assert resp.json()["mode"] == "human"
        assert any(m["text"] == "Happy to help! What's the project?" for m in resp.json()["messages"])

        # And a further visitor message does NOT get an AI reply -- mode is human.
        resp = await visitor.post("/api/chat", json={"text": "It's for a sneaker launch", "threadId": thread_id})
        assert resp.json()["reply"] == ""
        assert resp.json()["mode"] == "human"
    finally:
        await visitor.aclose()
        await admin.aclose()


async def test_handback_to_ai_retains_full_history_including_admin_messages(admin_user, configured_ai):
    """The core requirement from the design discussion: when a thread
    goes human -> ai, the AI's NEXT call must be given the entire
    history, including what the admin said while it owned the thread --
    not a fresh/cold context."""
    from app.routers.chat import FORWARD_MARKER

    configured_ai["set_reply"](f"Connecting you. {FORWARD_MARKER}")
    visitor = await _new_client()
    admin = await _admin_client()
    try:
        resp = await visitor.post("/api/chat", json={"text": "custom project, please help"})
        thread_id = resp.json()["threadId"]

        await admin.post(f"/api/admin/chat/threads/{thread_id}/reply", json={"text": "We can do a 10-photo package for $500."})

        resp = await admin.patch(f"/api/admin/chat/threads/{thread_id}/mode", json={"mode": "ai"})
        assert resp.status_code == 200
        assert resp.json()["mode"] == "ai"
        assert any(m["isSystem"] and "Handed back" in m["text"] for m in resp.json()["messages"])

        configured_ai["set_reply"]("Sounds good, want me to note anything else?")
        resp = await visitor.post("/api/chat", json={"text": "Sounds good, thanks!", "threadId": thread_id})
        assert resp.status_code == 200
        assert resp.json()["mode"] == "ai"

        # The exact assertion: the admin's $500 message was in what Gemini was given.
        sent_contents = configured_ai["captured_contents"]
        all_text = " ".join(part.text for c in sent_contents for part in c.parts)
        assert "$500" in all_text
        assert "10-photo package" in all_text
    finally:
        await visitor.aclose()
        await admin.aclose()


async def test_admin_can_explicitly_pick_up_without_replying_yet(admin_user, configured_ai):
    from app.routers.chat import FORWARD_MARKER

    configured_ai["set_reply"](f"Connecting you. {FORWARD_MARKER}")
    visitor = await _new_client()
    admin = await _admin_client()
    try:
        resp = await visitor.post("/api/chat", json={"text": "custom project"})
        thread_id = resp.json()["threadId"]

        resp = await admin.patch(f"/api/admin/chat/threads/{thread_id}/mode", json={"mode": "human"})
        assert resp.status_code == 200
        assert resp.json()["mode"] == "human"
    finally:
        await visitor.aclose()
        await admin.aclose()


async def test_non_admin_cannot_access_chat_admin_endpoints(customer_user):
    customer = await _customer_client()
    try:
        resp = await customer.get("/api/admin/chat/threads")
        assert resp.status_code == 401
    finally:
        await customer.aclose()


# ============================================================
# Rate limiting
# ============================================================


async def test_chat_rate_limited(monkeypatch, configured_ai):
    import app.core.config as config_module

    settings = config_module.get_settings()
    monkeypatch.setattr(settings, "AI_RATE_LIMIT_MAX_REQUESTS", 2)

    client = await _new_client()
    try:
        for _ in range(2):
            resp = await client.post("/api/chat", json={"text": "hi"})
            assert resp.status_code == 200

        resp = await client.post("/api/chat", json={"text": "hi again"})
        assert resp.status_code == 429
    finally:
        await client.aclose()
