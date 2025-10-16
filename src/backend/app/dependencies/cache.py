from typing import Annotated
from fastapi import Depends
import redis.asyncio as redis
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# TODO: remove the global
_redis_client: redis.Redis | None = None


async def get_redis_client() -> redis.Redis:
    """Dependency that provides a Redis client."""
    global _redis_client
    
    if _redis_client is None:
        _redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            decode_responses=True
        )
        logger.info("Redis client initialized")
    
    return _redis_client


async def close_redis_client():
    """Close the Redis client on shutdown."""
    global _redis_client
    
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
        logger.info("Redis client closed")


# Type alias for dependency injection
RedisClient = Annotated[redis.Redis, Depends(get_redis_client)]