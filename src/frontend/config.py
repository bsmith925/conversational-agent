from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Frontend settings using Pydantic
    Reads from environment variables or .env file
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Backend connection settings
    backend_url: str = "http://localhost:8000"
    ws_url: str = "ws://localhost:8000/ws"
    
    # Frontend specific settings
    chainlit_host: str = "0.0.0.0"
    chainlit_port: int = 8000
    
settings = Settings()

