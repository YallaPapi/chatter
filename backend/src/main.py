from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown events."""
    settings = get_settings()
    print(f"Starting {settings.app_name} v{settings.app_version}")

    # Startup: Initialize resources here
    # TODO: Initialize database connection pool
    # TODO: Initialize ChromaDB client
    # TODO: Load knowledge base embeddings

    yield

    # Shutdown: Cleanup resources here
    print("Shutting down...")


def create_app() -> FastAPI:
    """Application factory."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="AI-powered assistant for OnlyFans chatters - get real-time recommendations based on proven techniques",
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routes
    register_routes(app)

    return app


def register_routes(app: FastAPI) -> None:
    """Register all API routes."""

    @app.get("/health")
    async def health_check() -> dict:
        """Health check endpoint."""
        return {
            "status": "healthy",
            "version": get_settings().app_version,
        }

    @app.get("/")
    async def root() -> dict:
        """Root endpoint with API information."""
        return {
            "name": "Chatter Copilot API",
            "version": get_settings().app_version,
            "docs": "/docs",
            "health": "/health",
        }

    # Register API routers
    from .api import recommend
    app.include_router(recommend.router, prefix="/api/v1")


# Create the app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
