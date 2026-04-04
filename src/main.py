"""FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.utils.logger import setup_logging
from src.api.webhook import router as webhook_router
from src.db import engine, Base

# Setup logging
logger = setup_logging(level=settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan (startup/shutdown)."""
    # Startup
    logger.info("Starting Telegram Webhook Menu Backend")

    # Create tables (in development; production uses alembic migrations)
    if settings.is_development:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created")

    yield

    # Shutdown
    logger.info("Shutting down application")


# Create FastAPI application
app = FastAPI(
    title="Telegram Webhook Menu Backend",
    description="FastAPI backend for managing Telegram bot webhook and menu routing",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware (restrict to trusted origins in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.is_development else ["https://api.telegram.org"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(webhook_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "Telegram Webhook Menu Backend",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "webhook": "/webhook",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.is_development,
        log_level=settings.log_level.lower(),
    )
