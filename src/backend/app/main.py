from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import setup_logging
from app.dependencies.cache import close_redis_client
from app.api.routes import chat, health, websocket


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    setup_logging()
    yield
    await close_redis_client()


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
    app.include_router(websocket.router)  # No prefix for WebSocket
    
    return app


app = create_app()