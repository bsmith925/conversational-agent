from typing import List, Optional
import redis.asyncio as redis
from .base import DatabaseService
from app.core.logging import get_logger

logger = get_logger(__name__)


class RedisDatabase(DatabaseService):
    """Generic Redis database operations."""

    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client

    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        """Set a key-value pair with optional TTL."""
        try:
            if ttl:
                await self.redis_client.setex(key, ttl, value)
            else:
                await self.redis_client.set(key, value)
        except Exception as e:
            logger.error(f"Redis SET failed for key {key}: {e}", exc_info=True)
            raise

    async def get(self, key: str) -> Optional[str]:
        """Get a value by key."""
        try:
            return await self.redis_client.get(key)
        except Exception as e:
            logger.error(f"Redis GET failed for key {key}: {e}", exc_info=True)
            return None

    async def lpush(self, key: str, *values: str) -> None:
        """Push values to the left of a list."""
        try:
            await self.redis_client.lpush(key, *values)
        except Exception as e:
            logger.error(f"Redis LPUSH failed for key {key}: {e}", exc_info=True)
            raise

    async def lrange(self, key: str, start: int, end: int) -> List[str]:
        """Get a range of values from a list."""
        try:
            return await self.redis_client.lrange(key, start, end)
        except Exception as e:
            logger.error(f"Redis LRANGE failed for key {key}: {e}", exc_info=True)
            return []

    async def delete(self, key: str) -> None:
        """Delete a key."""
        try:
            await self.redis_client.delete(key)
        except Exception as e:
            logger.error(f"Redis DELETE failed for key {key}: {e}", exc_info=True)
            raise

    async def expire(self, key: str, ttl: int) -> None:
        """Set expiration for a key."""
        try:
            await self.redis_client.expire(key, ttl)
        except Exception as e:
            logger.error(f"Redis EXPIRE failed for key {key}: {e}", exc_info=True)
            raise

    async def execute_query(self, sql: str, params: tuple = None) -> List[dict]:
        """Redis doesn't use SQL - this is for interface compatibility."""
        logger.warning("execute_query called on Redis database - not applicable")
        return []
