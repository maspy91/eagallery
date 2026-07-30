import redis.asyncio as redis
from app.core.config import get_settings

settings = get_settings()

redis_url = settings.REDIS_URL or "redis://localhost:6379/0"

# Fix missing scheme if plain host was passed
if not redis_url.startswith(("redis://", "rediss://", "unix://")):
    redis_url = f"redis://{redis_url}"

# Extra kwargs for TLS/Upstash connections
extra_kwargs = {}
if redis_url.startswith("rediss://"):
    extra_kwargs["ssl_cert_reqs"] = None

redis_client = redis.from_url(
    redis_url,
    decode_responses=True,
    socket_connect_timeout=2,
    socket_timeout=2,
    **extra_kwargs,
)


async def get_redis() -> redis.Redis:
    return redis_client