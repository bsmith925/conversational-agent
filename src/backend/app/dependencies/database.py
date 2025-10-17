from typing import Annotated
from functools import lru_cache
from fastapi import Depends
import psycopg
from psycopg import AsyncConnection
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def get_connection_pool() -> psycopg.AsyncConnectionPool:
    """Dependency that provides a singleton connection pool."""
    return psycopg.AsyncConnectionPool(
        settings.postgres_dsn,
        min_size=2,
        max_size=10,
        kwargs={"autocommit": True}
    )


async def get_db_connection(pool: psycopg.AsyncConnectionPool = Depends(get_connection_pool)) -> AsyncConnection:
    """Dependency that provides a database connection from the pool."""
    return await pool.getconn()


# Type aliases for dependency injection
DatabaseConnection = Annotated[AsyncConnection, Depends(get_db_connection)]
