# Deploying EddyArt Gallery — Render (backend) + Vercel (frontend)

This covers: provisioning Neon/Upstash, deploying the backend to Render,
deploying the frontend to Vercel, and testing the whole auth system back to
back, both locally and once deployed.

## Architecture

The frontend calls the backend's Render URL **directly, cross-site**
(`PUBLIC_API_URL` in the frontend's `.env`) — not through a same-origin
proxy. That means:

- Session cookies are `SameSite=None; Secure` in production (the backend's
  default — see `COOKIE_SAMESITE` in `app/core/config.py`), which requires
  HTTPS on both ends. Render and Vercel both give you HTTPS by default, so
  this just works once both are deployed.
- CORS on the backend must list the frontend's exact origin(s)
  (`ALLOWED_ORIGINS`) — this is load-bearing, not optional, with this setup.
- Caveat: third-party (cross-site) cookies are what Safari's ITP and
  Chrome's ongoing phase-out specifically target. If you hit login "working"
  but the session not persisting in a particular browser down the road, the
  fix is to instead proxy `/api/*` through a Vercel rewrite so every request
  is same-origin from the browser's point of view (set `COOKIE_SAMESITE=lax`
  on the backend if you do this). Not needed to get started.

## 1. Provision Neon (Postgres) and Upstash (Redis)

- **Neon**: create a project, copy the connection string, and convert it to
  the asyncpg form the backend expects:
  `postgresql+asyncpg://user:password@host/dbname?ssl=require`
  (Neon gives you `sslmode=require` — either form works, `app/core/config.py`
  normalizes `sslmode` → `ssl` automatically.)
- **Upstash**: create a Redis database, copy the **Redis protocol** URL
  (`rediss://default:password@....upstash.io:6379`) — not the REST API URL.

## 1b. Provision Supabase Storage (photo storage)

Photo uploads go **directly from the admin's browser to Supabase Storage**
using a signed upload URL the backend generates (`POST
/api/photos/upload-url`) — the file bytes never pass through the FastAPI
server. This means:

- Create a Supabase project and a Storage bucket (e.g. `photos`).
- Set `SUPABASE_URL`, `SUPABASE_KEY` (the **service role** key, not the
  anon key — the backend needs write access), and
  `SUPABASE_STORAGE_BUCKET`. All three are required together; the app
  refuses to start with only some of them set (see `app/core/config.py`).
- Make the bucket public (or serve it through a custom domain) so
  `public_url()` in `app/core/storage.py` resolves to something the
  browser can actually load.
- **Verify the upload flow specifically after any Supabase project
  changes** — signed-upload-URL semantics aren't identical to the
  S3-compatible presigned PUT this backend originally used (R2), so a
  config that "looks right" can still fail on the actual upload step.
  Test by uploading a real photo through **Admin → Photos** and
  confirming it appears with a working image, not just that the API
  calls return 200.

## 2. Deploy the backend to Render

**Option A — Blueprint (recommended):** push this repo, then in the Render
dashboard: New + → Blueprint → point it at the repo. Render reads
`render.yaml` and creates the service. You'll be prompted to fill in every
`sync: false` field (DATABASE_URL, REDIS_URL, FRONTEND_URL, ALLOWED_ORIGINS,
SMTP_*, ADMIN_EMAIL/PASSWORD, etc.) in the dashboard.

**Option B — Manual:** New + → Web Service → point at the repo.
- Build command: `pip install -r requirements.txt`
- Start command: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health check path: `/health`
- Set every variable from `.env.example` in the Environment tab.

Either way, on first deploy set `ADMIN_EMAIL` and `ADMIN_PASSWORD` — that's
the only way an admin account ever gets created (see
`app/core/bootstrap.py`). You can remove them after the first successful
deploy; re-running with them still set is a no-op once the account exists.

`alembic upgrade head` runs on every deploy, before the server starts, so
schema changes apply automatically — no manual migration step.

## 3. Deploy the frontend to Vercel

- Import the frontend repo into Vercel (framework preset: SvelteKit, this is
  auto-detected).
- Set the environment variable `PUBLIC_API_URL` to your Render backend's URL
  (e.g. `https://eddyart-gallery-backend.onrender.com`), no trailing slash.
- Deploy.
- Back in Render, set `ALLOWED_ORIGINS` to your Vercel URL(s)
  (`https://your-app.vercel.app`, plus any custom domain), and `FRONTEND_URL`
  to the primary one (used to build links in verification/reset/invite
  emails). Redeploy the backend if you change these after the first deploy.

## 4. Test back to back

### Locally, before deploying anything

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt   # includes requirements.txt + aiosqlite for tests
pytest                                # runs against an in-memory sqlite DB + fake Redis, no network needed
```

This exercises the full flows end to end: register → blocked before
verify → verify → session → me → logout; forgot → reset → old password
rejected, new one works; admin bootstrap → staff invite → accept → login →
permission boundary (staff can't manage roles) → revoke; confirms the
customer and admin login endpoints never cross-validate each other's
credentials; (`tests/test_photos.py`) upload → draft → publish →
view-count increments → like/unlike → edit → delete-with-storage-cleanup,
plus that drafts/flagged photos 404 for the public and a customer session
can't call any `photos:manage` endpoint; (`tests/test_comments.py`) guest
and customer comments, nested replies, moderation (flag/delete, cascades
to replies), and that a customer can't moderate; (`tests/test_conversations.py`)
a customer's thread, admin/staff reply (auto-flips status), permission
boundaries (customer can't list everyone's conversations or reply to
someone else's); and (`tests/test_notifications.py`) that a comment reply
and an admin conversation reply each produce the right notification (and
that self-replies and guest-authored parents produce none), plus
list/unread-count/mark-read/mark-all-read and that one customer can't see
or touch another's notifications. Storage (Supabase) is monkeypatched in
`test_photos.py` — no real bucket needed to run any of this.

Then run it for real, against your actual Neon/Upstash (or a local Postgres
+ Redis if you have them):

```bash
# still in backend/, with a real .env (see .env.example)
alembic upgrade head
uvicorn app.main:app --reload
```

```bash
# separate terminal
cd frontend
cp .env.example .env   # PUBLIC_API_URL=http://localhost:8000
npm install
npm run dev
```

Manual smoke test in the browser at http://localhost:5173:
1. `/register` → check the backend logs (DEBUG=True logs emails instead of
   sending them) for the verification link → visit it → you land on
   `/verify-email` signed in → `/dashboard` loads.
2. Log out, log back in at `/login` with the same credentials.
3. `/forgot-password` → grab the reset link from the logs → `/reset-password`
   → old password now rejected, new one works.
4. `/auth` with your `ADMIN_EMAIL`/`ADMIN_PASSWORD` → `/admin` loads →
   **Roles & Staff** → invite someone → grab the invite link from the logs →
   `/staff/accept-invite` → set a password → lands on `/admin` as staff.
5. As staff, confirm **Roles & Staff** is hidden from the nav (no
   `roles:manage` permission) and that visiting `/admin/roles` directly
   shows a 403 from the staff list call.
6. Back as admin, revoke the staff account → confirm they can no longer log
   in at `/auth`.
7. Still as admin, **Photos** → Upload photo → pick an image → it uploads
   directly to R2 (check the Network tab: a `PUT` to your R2 domain, not to
   the Render backend) and appears in the table as `draft` → an edit dialog
   pops up automatically — fill in a title/category → Save.
8. Click the `draft` badge to cycle it to `published` → open `/` in a new
   tab → the photo can now appear in Featured Collection (it's a random 9,
   so refresh a few times if you have more than 9 published).
9. Open the photo's detail page (`/image/<id>`) → view count should read at
   least 1 (it increments server-side on every fetch) → as a customer (not
   admin), click the like button → count goes up, button fills in → click
   again → unlikes.
10. Back in admin **Photos**, click the badge again to cycle to `flagged` →
    confirm the photo disappears from `/` and its detail page now 404s for
    a logged-out visitor, but staff/admin can still see it via **Photos**.
11. Delete a photo from the admin table → confirm it's gone from the list
    and its detail page now 404s. (The R2 object is deleted best-effort in
    the background — see `app/routers/photos.py::delete_photo` — a failure
    there doesn't block the row from being deleted.)

### After deploying to Render + Vercel

Same script as above, against the live URLs — except now DEBUG should be
False on Render, so emails actually send via your configured SMTP
(Mailtrap in staging is fine) instead of just logging. Same walkthrough,
checking your inbox instead of the logs for the verification/reset/invite
links.

### curl smoke test (either environment)

```bash
BASE=http://localhost:8000   # or your Render URL
curl -i "$BASE/health"
curl -i -X POST "$BASE/api/customer/register" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test User","email":"test@example.com","password":"password123"}'
# -> 201; check backend logs (or your inbox) for the verification link/token
curl -i -X POST "$BASE/api/customer/verify-email" \
  -H "Content-Type: application/json" \
  -d '{"token":"PASTE_TOKEN_HERE"}' -c cookies.txt
curl -i -b cookies.txt "$BASE/api/customer/me"

# Public photo listing (published only) -- works even with an empty catalog
curl -i "$BASE/api/photos?random=9"
```

### curl smoke test — comments, conversations, notifications (backend only)

Runs entirely against the API, no frontend needed. Assumes `cookies.txt`
from above still has a valid customer session, and that `$PHOTO_ID` is a
published photo's id (grab one from the `/api/photos` call above).

```bash
# Comment on a photo as the logged-in customer
curl -i -X POST "$BASE/api/photos/$PHOTO_ID/comments" \
  -H "Content-Type: application/json" -b cookies.txt \
  -d '{"text":"Great piece!"}'
# -> 201; copy the returned "id" as $COMMENT_ID

# Reply as a guest (no cookie) -- comments allow this by design
curl -i -X POST "$BASE/api/photos/$PHOTO_ID/comments" \
  -H "Content-Type: application/json" \
  -d "{\"text\":\"Agreed!\",\"parent_id\":\"$COMMENT_ID\"}"
# -> 201; the original commenter should now have a notification (see below)

curl -i "$BASE/api/photos/$PHOTO_ID/comments"
# -> 200; nested tree with the reply under the root comment

# Confirm the notification landed
curl -i -b cookies.txt "$BASE/api/notifications"
# -> 200; one comment_reply notification, read: false

# Start a conversation as the customer
curl -i -X POST "$BASE/api/conversations" \
  -H "Content-Type: application/json" -b cookies.txt \
  -d '{"subject":"Licensing question","text":"What are your rates?"}'
# -> 201; copy the returned "id" as $CONVERSATION_ID

# Log in as admin (separate cookie jar) and reply
curl -i -X POST "$BASE/api/auth/login" \
  -H "Content-Type: application/json" -c admin_cookies.txt \
  -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\"}"
curl -i -X POST "$BASE/api/conversations/$CONVERSATION_ID/messages" \
  -H "Content-Type: application/json" -b admin_cookies.txt \
  -d '{"text":"Our rates start at $80/image."}'
# -> 200; conversation status should now read "in_progress"

# Back as the customer -- a second notification should be waiting
curl -i -b cookies.txt "$BASE/api/notifications/unread-count"
# -> 200; {"count": 2}
```

## Rotating the admin password

`ADMIN_EMAIL`/`ADMIN_PASSWORD` only ever run once (bootstrap is a no-op if
the account already exists). To change the password afterward, use
`/forgot-password` → `/reset-password` like any other account — there's no
separate admin-only reset mechanism.
