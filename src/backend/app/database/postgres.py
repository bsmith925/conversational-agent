from typing import List, Dict, Any
from psycopg import AsyncConnection
from .base import DatabaseService
from app.core.logging import get_logger

logger = get_logger(__name__)


class PostgresDatabase(DatabaseService):
    """PostgreSQL implementation of database service."""

    def __init__(self, connection: AsyncConnection):
        self.connection = connection

    async def execute_query(
        self, sql: str, params: tuple = None
    ) -> List[Dict[str, Any]]:
        """Execute a PostgreSQL query and return results."""
        try:
            async with self.connection.cursor() as cursor:
                await cursor.execute(sql, params)

                # Get column names
                columns = (
                    [desc[0] for desc in cursor.description]
                    if cursor.description
                    else []
                )

                # Fetch all results
                results = []
                async for row in cursor:
                    results.append(dict(zip(columns, row)))

                return results

        except Exception as e:
            logger.error(f"Database query failed: {e}", exc_info=True)
            return []
