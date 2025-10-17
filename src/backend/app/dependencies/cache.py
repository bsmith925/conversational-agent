from typing import Annotated
from functools import lru_cache
from fastapi import Depends
import redis.asyncio as redis
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@lru_cache()
def get_redis_client() -> redis.Redis:
    """Dependency that provides a Redis client (singleton)."""
    client = redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        decode_responses=True
    )
    logger.info("Redis client initialized")
    return client


async def close_redis_client():
    """Close the Redis client on shutdown."""
    try:
        client = get_redis_client()
        await client.close()
        get_redis_client.cache_clear()
        logger.info("Redis client closed")
    except Exception as e:
        logger.error(f"Error closing Redis client: {e}")


# Type alias for dependency injection
RedisClient = Annotated[redis.Redis, Depends(get_redis_client)]