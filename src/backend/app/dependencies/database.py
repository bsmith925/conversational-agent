from typing import Annotated
from functools import lru_cache
from fastapi import Depends
from psycopg import AsyncConnection
import psycopg_pool
from app.core.config import settings
from app.core.logging import get_logger
from app.database import DatabaseService, PostgresDatabase, RedisDatabase
from app.dependencies.cache import get_redis_client

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def get_connection_pool() -> psycopg_pool.AsyncConnectionPool:
    """Dependency that provides a singleton connection pool."""
    try:
        # Create pool without opening it immediately since lru_cache is sync
        # TODO: look into alru_cache
        pool = psycopg_pool.AsyncConnectionPool(
            settings.postgres_dsn,
            min_size=2,
            max_size=10,
            kwargs={"autocommit": True},
            open=False,
        )
        logger.info("Database connection pool created")
        return pool
    except Exception as e:
        logger.error(f"Failed to create connection pool: {e}", exc_info=True)
        raise


async def get_db_connection(
    pool: psycopg_pool.AsyncConnectionPool = Depends(get_connection_pool),
) -> AsyncConnection:
    """Dependency that provides a database connection from the pool."""
    try:
        # Ensure pool is open
        try:
            await pool.open()
        except Exception:
            pass

        connection = await pool.getconn()
        # Test the connection. NOTE: Leaving for now. Consider removing later.
        async with connection.cursor() as cur:
            await cur.execute("SELECT 1")
        return connection
    except Exception as e:
        logger.error(f"Database connection failed: {e}", exc_info=True)
        raise


def get_database_service(connection=Depends(get_db_connection)) -> DatabaseService:
    """Request-scoped database service."""
    return PostgresDatabase(connection)


def get_redis_database(redis_client=Depends(get_redis_client)) -> RedisDatabase:
    """Dependency that provides a Redis database service."""
    return RedisDatabase(redis_client)


# Type aliases for dependency injection
DatabaseConnection = Annotated[AsyncConnection, Depends(get_db_connection)]
DatabaseServiceDep = Annotated[DatabaseService, Depends(get_database_service)]
RedisDatabaseDep = Annotated[RedisDatabase, Depends(get_redis_database)]
