import logging
from redis.exceptions import RedisError, TimeoutError
from app.core.redis import redis_client

logger = logging.getLogger(__name__)


async def check_and_increment(key: str, max_attempts: int, window_seconds: int) -> tuple[bool, int]:
    """Returns (allowed, seconds_until_reset). EXPIRE only fires on the first
    increment, so a burst can't each reset the window."""
    try:
        pipe = redis_client.pipeline()
        pipe.incr(key)
        pipe.ttl(key)
        count, ttl = await pipe.execute()

        if ttl == -1:
            await redis_client.expire(key, window_seconds)
            ttl = window_seconds

        if count > max_attempts:
            return False, max(1, ttl)

        return True, 0

    except (RedisError, TimeoutError) as e:
        logger.warning(f"Redis unavailable for rate limiting on '{key}': {e}")
        # Fallback: allow request if Redis is down/unreachable
        return True, 0