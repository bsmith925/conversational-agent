from abc import ABC, abstractmethod
from typing import List, Dict, Any


class DatabaseService(ABC):
    """Base class for database services."""

    @abstractmethod
    async def execute_query(
        self, sql: str, params: tuple = None
    ) -> List[Dict[str, Any]]:
        """Execute a database query and return results."""
        pass
