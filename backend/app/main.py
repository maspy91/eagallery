import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

from app.core.bootstrap import ensure_admin_bootstrap
from app.core.config import get_settings
from app.core.database import Base, engine
from app.core.model_registry import discover_models
from app.core.redis import redis_client
from app.core.storage import ensure_bucket
from app.routers import admin_auth, ai, chat, comments, conversations, customer_auth, notifications, photos, videos

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    discovered = discover_models()
    logger.info(f"Model auto-discovery imported {len(discovered)} modules under app/")

    try:
        if settings.DEBUG:
            # Local/dev convenience only. In production, tables are created
            # by `alembic upgrade head` (see render.yaml / DEPLOY.md) --
            # create_all is not a substitute for migrations once there's
            # real data, so it deliberately only runs in DEBUG.
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:
        logger.warning("Database initialization skipped due to error: %s", exc)

    try:
        await redis_client.ping()
        logger.info("Redis (Upstash) connection OK")
    except Exception as exc:
        logger.warning("Redis connection unavailable during startup: %s", exc)

    try:
        await ensure_admin_bootstrap()
    except Exception as exc:
        logger.warning("Admin bootstrap skipped due to error: %s", exc)

    try:
        # Idempotent -- creates the bucket with these limits if it
        # doesn't exist yet, or updates an existing one to match. See
        # ensure_bucket()'s docstring for why this is where the real
        # 10MB/5MB enforcement actually lives (Supabase Storage itself,
        # not app code). No-ops cleanly if Supabase isn't configured at
        # all (get_supabase_client() returns None), same as every other
        # optional integration in this startup sequence.
        if settings.SUPABASE_STORAGE_BUCKET:
            await run_in_threadpool(
                ensure_bucket,
                settings.SUPABASE_STORAGE_BUCKET,
                public=True,
                file_size_limit=settings.MAX_PHOTO_SIZE_BYTES,
                allowed_mime_types=["image/jpeg", "image/png", "image/webp", "image/gif"],
            )
        if settings.SUPABASE_VIDEO_BUCKET:
            await run_in_threadpool(
                ensure_bucket,
                settings.SUPABASE_VIDEO_BUCKET,
                public=True,
                file_size_limit=settings.MAX_VIDEO_SIZE_BYTES,
                allowed_mime_types=["video/mp4"],
            )
    except Exception as exc:
        logger.warning("Storage bucket provisioning skipped due to error: %s", exc)

    yield

    try:
        await redis_client.aclose()
    except Exception:
        pass


app = FastAPI(title=settings.APP_NAME, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(customer_auth.router)
app.include_router(admin_auth.router)
app.include_router(photos.router)
app.include_router(videos.router)
app.include_router(comments.photo_comments_router)
app.include_router(comments.video_comments_router)
app.include_router(comments.moderation_router)
app.include_router(conversations.router)
app.include_router(notifications.router)
app.include_router(ai.router)
app.include_router(chat.router)
app.include_router(chat.admin_router)

# Future domain routers (analytics, etc.) get included here the same way.


@app.get("/")
def root():
    return {
        "message": f"{settings.APP_NAME} backend running",
        "debug_mode": settings.DEBUG,
        "turnstile_enabled": settings.TURNSTILE_ENABLED,
    }


@app.get("/health")
async def health():
    await redis_client.ping()
    return {"status": "ok"}
