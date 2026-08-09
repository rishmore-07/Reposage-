"""
app/main.py

FastAPI application factory.

This module creates the FastAPI application instance and wires together:
- Middleware (CORS, request ID, timing)
- Exception handlers
- Routers (health check + versioned API)
- Startup/shutdown lifecycle events

Design principle: this file is a wiring module only.
No business logic, no DB queries, no service calls.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.core.middleware import setup_exception_handlers, setup_middleware
from app.core.schemas import HealthResponse
from app.db.init_db import check_db_connection, dispose_engine

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    FastAPI lifespan context manager.

    Runs startup code before yielding, and shutdown code after.
    This replaces the deprecated @app.on_event("startup") pattern.
    """
    # ── Startup ───────────────────────────────────────────────────────────────
    configure_logging()
    logger.info(
        "application_starting",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
    )

    db_ok = await check_db_connection()
    if not db_ok:
        logger.error("startup_failed_database_unreachable")
        # In production, you might want to exit here to trigger a container restart
        # raise RuntimeError("Database is unreachable — cannot start.")

    logger.info("application_started")

    yield  # Application is running — handle requests

    # ── Shutdown ──────────────────────────────────────────────────────────────
    logger.info("application_shutting_down")
    await dispose_engine()
    logger.info("application_stopped")


def create_app() -> FastAPI:
    """
    Application factory — creates and configures the FastAPI instance.

    Using a factory function (instead of a module-level app = FastAPI())
    makes the app testable: tests can call create_app() with different
    settings without affecting the production instance.
    """
    app = FastAPI(
        title=settings.app_name,
        description=(
            "AI-powered GitHub repository intelligence platform. "
            "Analyze codebases, detect drift, and generate documentation automatically."
        ),
        version=settings.app_version,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # Register middleware (order matters — see middleware.py for details)
    setup_middleware(app)

    # Register global exception handlers
    setup_exception_handlers(app)

    # ── Health check endpoint ─────────────────────────────────────────────────
    @app.get(
        "/health",
        response_model=HealthResponse,
        tags=["Health"],
        summary="Application health check",
        description=(
            "Returns the current health status of the application. "
            "Used by load balancers, orchestrators, and monitoring systems."
        ),
    )
    async def health_check() -> HealthResponse:
        """
        Health check endpoint.

        Checks:
        - Application is running (implicit — if this returns, it's up)
        - Database connectivity

        Returns HTTP 200 if healthy, HTTP 503 if degraded.
        """
        db_ok = await check_db_connection()
        status = "ok" if db_ok else "degraded"

        return HealthResponse(
            status=status,
            version=settings.app_version,
            environment=settings.app_env,
            database="ok" if db_ok else "error",
        )

    # ── API routes ────────────────────────────────────────────────────────────
    app.include_router(api_router, prefix=settings.api_prefix)

    return app


# Module-level app instance used by uvicorn/gunicorn
app = create_app()
