from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.dependencies.cache import close_redis_client
from app.api.routes import chat, health, websocket

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    setup_logging()
    
    # Test critical dependencies
    try:
        from app.dependencies.database import get_connection_pool
        from app.dependencies.cache import get_redis_client
        
        # Test database
        pool = get_connection_pool()
        await pool.open()
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1")
        
        # Test Redis
        redis_client = get_redis_client()
        await redis_client.ping()
        
        logger.info("All dependencies initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize dependencies: {e}", exc_info=True)
        raise
    
    yield
    await close_redis_client()
    
    # Close database connection pool
    try:
        from app.dependencies.database import get_connection_pool
        pool = get_connection_pool()
        await pool.close()
        logger.info("Database connection pool closed")
    except Exception as e:
        logger.error(f"Error closing database connection pool: {e}")


def create_app() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title=settings.api_title,
        version=settings.api_version,
        lifespan=lifespan
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(health.router, prefix=settings.api_prefix)
    app.include_router(chat.router, prefix=settings.api_prefix)
    # No prefix for WebSocket
    app.include_router(websocket.router)  
    
    return app


app = create_app()
