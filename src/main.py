"""FastAPI application entry point."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config import settings
from src.utils.logger import setup_logging
from src.api.webhook import router as webhook_router
from src.api.admin import router as admin_router
from src.db import engine, Base
from src.models import *  # noqa: F401, F403 - Registers all models with Base

# Setup logging
logger = setup_logging(level=settings.log_level)


def is_admin_request(request: Request) -> bool:
    """Return whether a request targets the admin API."""
    return request.url.path.startswith("/admin")


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
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def handle_http_exception(request: Request, exc: HTTPException):
    """Normalize admin HTTP error responses."""
    if is_admin_request(request):
        return JSONResponse(
            status_code=exc.status_code,
            content={"ok": False, "error": str(exc.detail)},
        )
    return await http_exception_handler(request, exc)


@app.exception_handler(RequestValidationError)
async def handle_validation_exception(request: Request, exc: RequestValidationError):
    """Normalize admin validation error responses."""
    if is_admin_request(request):
        first_error = exc.errors()[0] if exc.errors() else {}
        return JSONResponse(
            status_code=422,
            content={"ok": False, "error": first_error.get("msg", "Validation error")},
        )
    return await request_validation_exception_handler(request, exc)


@app.exception_handler(Exception)
async def handle_unexpected_exception(request: Request, exc: Exception):
    """Return admin-compatible 500 responses."""
    logger.exception("Unhandled exception while serving request")
    if is_admin_request(request):
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": "Internal server error"},
        )
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})

# Include routers
app.include_router(webhook_router)
app.include_router(admin_router)


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
