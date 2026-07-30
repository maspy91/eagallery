# from functools import lru_cache
# from pathlib import Path
# from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# from pydantic import model_validator
# from pydantic_settings import BaseSettings, SettingsConfigDict

# # Resolves the absolute path to the 'backend' directory where the .env file lives.
# # Path(__file__) -> app/core/config.py
# # .parent -> app/core
# # .parent.parent -> app
# # .parent.parent.parent -> backend (root)
# BASE_DIR = Path(__file__).resolve().parent.parent.parent


# class Settings(BaseSettings):
#     model_config = SettingsConfigDict(
#         env_file=BASE_DIR / ".env",
#         env_file_encoding="utf-8",
#         extra="ignore",
#     )

#     # ---- Application ----
#     APP_NAME: str = "Future Gallery"
#     DEBUG: bool = True
#     # DEBUG=True: emails are logged instead of sent, Turnstile can be
#     # bypassed (see TURNSTILE_ENABLED below), and error responses may
#     # include more detail. Always False in production.

#     FRONTEND_URL: str = "http://localhost:5173"

#     # ---- Database (Neon Postgres) ----
#     # No local fallback on purpose -- this is the real, decided datastore.
#     # Neon's free tier works fine for local dev too, via a branch database,
#     # so there's no reason to special-case sqlite here.
#     DATABASE_URL: str

#     # ---- Redis (Upstash) ----
#     # Backs rate limiting and cross-instance chat pub/sub. Use the
#     # Redis-protocol endpoint (rediss://...) from the Upstash dashboard,
#     # not the REST API URL.
#     REDIS_URL: str

#     # ---- Security / JWT ----
#     SECRET_KEY: str
#     ALGORITHM: str = "HS256"
#     ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
#     MIN_PASSWORD_LENGTH: int = 8

#     # ---- Cloudflare Turnstile ----
#     # False = no Cloudflare dependency, fully offline dev.
#     # True  = REQUIRES TURNSTILE_SECRET, or the app refuses to start.
#     TURNSTILE_ENABLED: bool = False
#     TURNSTILE_SECRET: str | None = None

#     # ---- Email (Mailtrap in staging, real sender in prod) ----
#     EMAIL_VERIFICATION_TOKEN_TTL_HOURS: int = 24
#     PASSWORD_RESET_TOKEN_TTL_MINUTES: int = 30
#     SMTP_HOST: str = "sandbox.smtp.mailtrap.io"
#     SMTP_PORT: int = 2525
#     SMTP_USERNAME: str | None = None
#     SMTP_PASSWORD: str | None = None
#     SMTP_FROM_EMAIL: str = "noreply@futuregallery.app"
#     SMTP_FROM_NAME: str = "Future Gallery"
#     SMTP_USE_TLS: bool = True

#     # ---- Cloudflare R2 (photo storage) ----
#     R2_ACCOUNT_ID: str | None = None
#     R2_ACCESS_KEY_ID: str | None = None
#     R2_SECRET_ACCESS_KEY: str | None = None
#     R2_BUCKET: str | None = None
#     R2_PUBLIC_URL: str | None = None  # public bucket domain or custom domain, for serving images

#     # ---- AI feature ----
#     AI_API_KEY: str | None = None
#     AI_RATE_LIMIT_MAX_REQUESTS: int = 20
#     AI_RATE_LIMIT_WINDOW_MINUTES: int = 60

#     # ---- CORS ----
#     # Comma-separated exact origins. Never "*" -- browsers reject wildcard +
#     # credentials outright, and it defeats the purpose of the cookie-based
#     # session even where a proxy would let it through.
#     ALLOWED_ORIGINS: str = "http://localhost:5173"

#     # ---- Admin bootstrap ----
#     # The ONLY way an admin account is created. No public endpoint grants
#     # the admin role. Leave blank to skip bootstrap; set once, then rotate
#     # the password.
#     ADMIN_EMAIL: str | None = None
#     ADMIN_PASSWORD: str | None = None

#     # ---- Rate limiting (Redis-backed, shared across all Render instances) ----
#     RATE_LIMIT_LOGIN_MAX_ATTEMPTS: int = 5
#     RATE_LIMIT_LOGIN_WINDOW_MINUTES: int = 15
#     RATE_LIMIT_REGISTER_MAX_ATTEMPTS: int = 5
#     RATE_LIMIT_REGISTER_WINDOW_MINUTES: int = 60

#     # ---- Session cookies ----
#     # The frontend (Vercel) calls this backend's Render URL directly via
#     # PUBLIC_API_URL (see frontend/.env.example) -- that's cross-site from
#     # the browser's point of view, so cookies need SameSite=None, which in
#     # turn requires Secure=True (browsers reject Secure cookies over plain
#     # http, which is why local dev below overrides both to lax/non-secure).
#     # If you instead proxy /api/* through a Vercel rewrite so everything is
#     # same-origin, "lax" works too and is simpler -- see DEPLOY.md.
#     COOKIE_SAMESITE: str = "none"
#     # None = auto: secure unless DEBUG. Override explicitly if needed.
#     COOKIE_SECURE: bool | None = None

#     @property
#     def cookie_secure(self) -> bool:
#         return self.COOKIE_SECURE if self.COOKIE_SECURE is not None else not self.DEBUG

#     @property
#     def allowed_origins_list(self) -> list[str]:
#         return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

#     @model_validator(mode="after")
#     def _normalize_database_url(self):
#         if self.DATABASE_URL and "postgresql+asyncpg://" in self.DATABASE_URL:
#             parts = urlsplit(self.DATABASE_URL)
#             query_items = parse_qsl(parts.query, keep_blank_values=True)
#             normalized_items = []
#             converted_sslmode = False

#             for key, value in query_items:
#                 if key == "sslmode":
#                     normalized_items.append(("ssl", value))
#                     converted_sslmode = True
#                 else:
#                     normalized_items.append((key, value))

#             if converted_sslmode:
#                 self.DATABASE_URL = urlunsplit(
#                     (parts.scheme, parts.netloc, parts.path, urlencode(normalized_items), parts.fragment)
#                 )

#         return self

#     @model_validator(mode="after")
#     def _validate_turnstile(self):
#         if self.TURNSTILE_ENABLED and not self.TURNSTILE_SECRET:
#             raise ValueError(
#                 "TURNSTILE_ENABLED=True requires TURNSTILE_SECRET to be set. "
#                 "Set TURNSTILE_ENABLED=False for local/offline testing instead."
#             )
#         return self

#     @model_validator(mode="after")
#     def _validate_r2(self):
#         r2_fields = [self.R2_ACCOUNT_ID, self.R2_ACCESS_KEY_ID, self.R2_SECRET_ACCESS_KEY, self.R2_BUCKET]
#         if any(r2_fields) and not all(r2_fields):
#             raise ValueError(
#                 "Partial R2 configuration detected. Set all of R2_ACCOUNT_ID, "
#                 "R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET, or none of them."
#             )
#         return self


# @lru_cache()
# def get_settings() -> Settings:
#     return Settings()


#================================
from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolves the absolute path to the project root directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- Application ----
    APP_NAME: str = "Future Gallery"
    DEBUG: bool = True
    FRONTEND_URL: str = "http://localhost:5173"

    # ---- Database (Neon Postgres) ----
    DATABASE_URL: str

    # ---- Redis (Upstash) ----
    REDIS_URL: str

    # ---- Security / JWT ----
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    MIN_PASSWORD_LENGTH: int = 8

    # ---- Cloudflare Turnstile ----
    TURNSTILE_ENABLED: bool = False
    TURNSTILE_SECRET: str | None = None

    # ---- Email (Mailtrap in staging, real sender in prod) ----
    EMAIL_VERIFICATION_TOKEN_TTL_HOURS: int = 24
    PASSWORD_RESET_TOKEN_TTL_MINUTES: int = 30
    SMTP_HOST: str = "sandbox.smtp.mailtrap.io"
    SMTP_PORT: int = 2525
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM_EMAIL: str = "noreply@futuregallery.app"
    SMTP_FROM_NAME: str = "Future Gallery"
    SMTP_USE_TLS: bool = True

    # ---- Supabase Storage (Photo Storage) ----
    SUPABASE_URL: str | None = None
    SUPABASE_KEY: str | None = None  # Service role key recommended for backend operations
    SUPABASE_STORAGE_BUCKET: str | None = None  # e.g., "photos"

    # ---- AI feature ----
    AI_API_KEY: str | None = None
    AI_RATE_LIMIT_MAX_REQUESTS: int = 20
    AI_RATE_LIMIT_WINDOW_MINUTES: int = 60

    # ---- CORS ----
    ALLOWED_ORIGINS: str = "http://localhost:5173"

    # ---- Admin bootstrap ----
    ADMIN_EMAIL: str | None = None
    ADMIN_PASSWORD: str | None = None

    # ---- Rate limiting ----
    RATE_LIMIT_LOGIN_MAX_ATTEMPTS: int = 5
    RATE_LIMIT_LOGIN_WINDOW_MINUTES: int = 15
    RATE_LIMIT_REGISTER_MAX_ATTEMPTS: int = 5
    RATE_LIMIT_REGISTER_WINDOW_MINUTES: int = 60

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @model_validator(mode="after")
    def _validate_turnstile(self):
        if self.TURNSTILE_ENABLED and not self.TURNSTILE_SECRET:
            raise ValueError(
                "TURNSTILE_ENABLED=True requires TURNSTILE_SECRET to be set. "
                "Set TURNSTILE_ENABLED=False for local/offline testing instead."
            )
        return self

    @model_validator(mode="after")
    def _validate_supabase(self):
        sp_fields = [self.SUPABASE_URL, self.SUPABASE_KEY, self.SUPABASE_STORAGE_BUCKET]
        if any(sp_fields) and not all(sp_fields):
            raise ValueError(
                "Partial Supabase Storage configuration detected. Set all of SUPABASE_URL, "
                "SUPABASE_KEY, and SUPABASE_STORAGE_BUCKET, or none of them."
            )
        return self


@lru_cache()
def get_settings() -> Settings:
    return Settings()