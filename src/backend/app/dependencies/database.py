from typing import Annotated
from functools import lru_cache
from fastapi import Depends
from psycopg import AsyncConnection
import psycopg_pool
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def get_connection_pool() -> psycopg_pool.AsyncConnectionPool:
    """Dependency that provides a singleton connection pool."""
    try:
        # Create pool without opening it immediately since lru_cache is sync
        pool = psycopg_pool.AsyncConnectionPool(
            settings.postgres_dsn,
            min_size=2,
            max_size=10,
            kwargs={"autocommit": True},
            open=False 
        )
        logger.info("Database connection pool created")
        return pool
    except Exception as e:
        logger.error(f"Failed to create connection pool: {e}", exc_info=True)
        raise


async def get_db_connection(pool: psycopg_pool.AsyncConnectionPool = Depends(get_connection_pool)) -> AsyncConnection:
    """Dependency that provides a database connection from the pool."""
    try:
        # Ensure pool is open
        try:
            await pool.open()
        except Exception:
            pass
        
        connection = await pool.getconn()
        # Test the connection. NOTE: Leaving for now. Remove later.
        async with connection.cursor() as cur:
            await cur.execute("SELECT 1")
        return connection
    except Exception as e:
        logger.error(f"Database connection failed: {e}", exc_info=True)
        raise


# Type aliases for dependency injection
DatabaseConnection = Annotated[AsyncConnection, Depends(get_db_connection)]
