# EddyArt Gallery — SvelteKit frontend (Phase 2: auth + photo management wired to FastAPI)

SvelteKit conversion of the original React/Vite draft. Phase 1 was UI-only on
mock data. Phase 2 wires real authentication/authorization and **real photo
management** to the FastAPI backend — registration, email verification,
login/logout, password recovery, staff invites, and now photo upload,
publishing, likes, and view counts all hit real endpoints and real storage
(Cloudflare R2 + Neon Postgres). Comments, conversations, and notifications
are still mock/in-memory, pending a later phase.

## Run it

```bash
cp .env.example .env   # set PUBLIC_API_URL to your backend (default: http://localhost:8000)
npm install
npm run dev
```

Open http://localhost:5173. You'll need the backend running too — see
`../backend/DEPLOY.md` for local setup and Render/Vercel deployment.

## Accounts

Two **completely separate** login systems, backed by two separate sets of
backend endpoints (see the backend's `app/routers/customer_auth.py` and
`app/routers/admin_auth.py`):

- **Customers** register at `/register` (real account, email verification
  required before first login) and sign in at `/login`.
- **Admin/staff** sign in at `/auth` (not linked from customer-facing pages
  except a small icon). The only admin account is created by the backend's
  `ADMIN_EMAIL`/`ADMIN_PASSWORD` bootstrap (see `app/core/bootstrap.py`) — there
  is no public admin signup. Staff accounts are created by an admin via
  **Roles & Staff** → invite, which emails a link to `/staff/accept-invite`.

Both flows share **Forgot password?** → `/forgot-password` → `/reset-password`,
which really does email a single-use, time-limited token now.

## What's real vs. placeholder right now

| Area | Status |
|---|---|
| Routing, layout, navbar (3 states: guest / customer / admin-staff) | Real |
| Light/dark theme (persisted, no FOUC) | Real |
| Customer registration, email verification, login, logout | **Real** — FastAPI + Argon2 + Neon Postgres |
| Admin/staff login, logout | **Real** |
| Staff invite / accept-invite / list / revoke | **Real**, gated by the `roles:manage` permission |
| Forgot / reset password (shared by both account types) | **Real** — single-use, time-limited tokens |
| Session | **Real** — httpOnly cookie, not localStorage/sessionStorage |
| Admin/customer route guards | Client-side only (see below) |
| Photo upload, publish/draft/flag, edit, delete | **Real** — direct-to-R2 presigned upload, gated by `photos:manage` |
| Gallery grid (Featured Collection), image detail page | **Real** — fetched from `/api/photos`, random 9 picked server-side |
| Photo view counts, likes | **Real** — view count increments server-side on fetch; likes require a customer session |
| Comments UI on the image detail page | Real UI, still mock data (not yet tied to real photo IDs) |
| Admin dashboard (comments, requests), customer dashboard (notifications/inbox/conversations) | Real UI, mock data, in-memory only |
| Turnstile / bot protection | Wired end-to-end but `TURNSTILE_ENABLED=False` by default — see backend `.env.example` |

## Roles

- `admin` — full access, including assigning/revoking the `staff` role
- `staff` — admin-assigned; everything `admin` can do **except** managing roles
- `customer` — self-registers; gets a dashboard (notifications, inbox, conversation follow-up), no admin capabilities

See `src/lib/types.ts` (`ROLE_PERMISSIONS`) for the client-side copy, and the
backend's `app/core/permissions.py` for the copy that's actually enforced.

## Two separate login systems

Customer login/register and admin/staff login are intentionally distinct —
different pages, different cookies (`customer_session` vs `admin_session`),
different backend routers, different rate-limit buckets. Brute-forcing the
customer login can never be used to probe or lock out admin credentials,
because the customer endpoints never query rows where `role != 'customer'`.
See the comment block at the top of `src/lib/stores/auth.ts` and
`backend/app/models/user.py`.

## Known gap: route guards are still client-side

`admin/+layout.svelte` and `dashboard/+layout.svelte` redirect based on the
`currentUser` store, which is hydrated by asking the backend "who am I?" on
load (`restoreSession()`). This is fine for UX (no flash of protected content
before the redirect fires) but is **not** the real security boundary — that's
the backend, which independently re-checks the session cookie on every
`/api/customer/*` or `/api/auth/*` call regardless of what the client shows.
A further hardening step (not done here) is moving these guards into
`+layout.server.ts` so the protected page's HTML/JS is never even sent to an
unauthenticated request.

## Notes on the theme system

- Tokens live in `src/app.css` as HSL triplets under `:root` (light) and
  `.dark` (dark, the original draft's palette — kept as brand default).
- `src/app.html` sets the `.dark` class before hydration to avoid a flash of
  the wrong theme.
- `src/lib/stores/theme.ts` is the toggle; it writes to `localStorage` (fine
  here — this is a real deployed app, not a sandboxed artifact).
