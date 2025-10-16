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
        case_sensitive=False,
    )

    # API Settings
    api_title: str = "Conversational Agent API"
    api_version: str = "1.0.0"
    api_prefix: str = "/api/v1"
    
    # TODO: CORS here and use in main.py

    # Database (Postgres) settings
    database_username: str = "user"
    database_password: str = "password1230"
    database_host: str = "localhost"
    database_port: int = 5432
    database_name: str = "vectordb"

    # Redis settings
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_ttl: int = 3600
    # leaving redis_db to default as 0, especially considering cluster is always 0

    # LLM & Embedding Settings
    ollama_base_url: HttpUrl = "http://localhost:11434"
    llm_model: str = "llama3"
    embedding_model_name: str = "all-MiniLM-L6-v2"

    openrouter_api_key: str = ""
    
    # RAG Settings
    retrieval_similarity_threshold: float = 0.3
    llm_max_tokens: int = 4096 # increased from 2k, was truncating. Need to handle truncations better..e.g. how claude UI says max convo context. Continue button?
    enable_query_expansion: bool = False
    rag_k: int = 3
    chat_history_limit: int = 20
    
    # Logging
    log_level: str = "INFO"
    
    # Database Safety - too much docker-compose down -v while iterating
    allow_db_recreation: bool = False

    @property
    def postgres_dsn(self) -> str:
        """
        Returns the DSN for both sync and async psycopg3 connections.
        Format: "dbname=... user=... password=... host=... port=..."
        """
        # won't need to specify driver if not using ORM that requires it like SQLAlchemy
        return PostgresDsn.build(
            scheme="postgresql",
            # hosts: multiple hosts good for fragmented DBs to build many hosts 
            username=self.database_username,
            password=self.database_password,
            host=self.database_host,
            port=int(self.database_port),
            path=self.database_name

        ).unicode_string() # stringify the URI from MultiHostURL
    
settings = Settings() # singleton we can import and avoid some ciruclar imports
