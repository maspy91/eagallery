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
    #-------Cookie settings for session management-------
    cookie_secure: bool = False
    cookie_samesite: str = "lax"

    # ---- Application ----
    APP_NAME: str = "Future Gallery"
    DEBUG: bool = False
    FRONTEND_URL: str

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
    SMTP_STARTTLS: bool = True
#   
    # ---- Supabase Storage (Photo Storage) ----
    SUPABASE_URL: str | None = None
    SUPABASE_KEY: str | None = None  # Service role key recommended for backend operations
    SUPABASE_STORAGE_BUCKET: str | None = None  # e.g., "photos"

    # ---- AI feature ----
    AI_API_KEY: str | None = None
    AI_RATE_LIMIT_MAX_REQUESTS: int = 20
    AI_RATE_LIMIT_WINDOW_MINUTES: int = 60

    # ---- Google OAuth2 (customer "Sign in with Google" only -- admin/
    # staff never authenticate this way, same reasoning as why they have
    # a separate login system from customers in the first place) ----
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None
    # Must exactly match a redirect URI registered in Google Cloud
    # Console (Credentials -> your OAuth client -> Authorized redirect
    # URIs) or Google rejects the callback. Points at the FRONTEND now
    # (proxied through to this backend via vercel.json / vite.config.ts),
    # not this backend's own URL directly -- that's what makes the
    # session cookie set during the OAuth callback land on the frontend's
    # own origin instead of this backend's, consistent with every other
    # login path post-proxy-migration.
    GOOGLE_REDIRECT_URI: str | None = None

    # ---- Admin bootstrap ----
    ADMIN_EMAIL: str | None = None
    ADMIN_PASSWORD: str | None = None

    # ---- Rate limiting ----
    RATE_LIMIT_LOGIN_MAX_ATTEMPTS: int = 5
    RATE_LIMIT_LOGIN_WINDOW_MINUTES: int = 15
    RATE_LIMIT_REGISTER_MAX_ATTEMPTS: int = 5
    RATE_LIMIT_REGISTER_WINDOW_MINUTES: int = 60


    ALLOWED_ORIGINS: str = "http://localhost:5173,https://eagallery-589t.vercel.app/"
    @property
    def allowed_origins_list(self) -> list[str]:
        # .rstrip("/") removes any accidental trailing slashes!
        return [origin.strip().rstrip("/") for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

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

    @model_validator(mode="after")
    def _validate_google_oauth(self):
        g_fields = [self.GOOGLE_CLIENT_ID, self.GOOGLE_CLIENT_SECRET, self.GOOGLE_REDIRECT_URI]
        if any(g_fields) and not all(g_fields):
            raise ValueError(
                "Partial Google OAuth configuration detected. Set all of GOOGLE_CLIENT_ID, "
                "GOOGLE_CLIENT_SECRET, and GOOGLE_REDIRECT_URI, or none of them."
            )
        return self


@lru_cache()
def get_settings() -> Settings:
    return Settings()
