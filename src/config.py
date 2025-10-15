from pydantic import HttpUrl, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Manage application settings using Pydantic
    Reads from environment variables or a .env file
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Database (Postgres) settings
    database_username: str = "user"
    database_password: str = "password"
    database_host: str = "localhost"
    database_port: int = 5432 # do I need to add field validator to coerce to int?
    database_name: str = "vectordb"

    # Redis settings
    redis_host: str = "localhost"
    redis_port: int = 6379
    # leaving redis_db to default as 0, especially considering cluster is always 0

    # LLM & Embedding Settings
    ollama_base_url: HttpUrl = "http://localhost:11434"
    llm_model: str = "llama3"
    embedding_model_name: str = "all-MiniLM-L6-v2"

    @property
    def postgres_dsn(self) -> str:
        """
        Returns the DSN for both sync and async psycopg3 connections.
        Format: "dbname=... user=... password=... host=... port=..."
        """
        # won't need to specify driver if not using ORM that requires it like SQLAlchemy
        return PostgresDsn.build(
            scheme="postgresql",
            # multiple hosts good for fragmented DBs to build many hosts
            username=self.database_username,
            password=self.database_password,
            host=self.database_host,
            port=int(self.database_port),
            path=self.database_name

        ).unicode_string() # stringify the URI from MultiHostURL
    
settings = Settings() #singleton we can import and avoid some ciruclar imports
