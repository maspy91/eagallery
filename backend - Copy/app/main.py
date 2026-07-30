import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.bootstrap import ensure_admin_bootstrap
from app.core.config import get_settings
from app.core.database import Base, engine
from app.core.model_registry import discover_models
from app.core.redis import redis_client
from app.routers import admin_auth, customer_auth, photos

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

# Future domain routers (comments, requests, analytics) get included here
# the same way, e.g.:
# app.include_router(comments_router)


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
