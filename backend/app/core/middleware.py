"""
app/core/middleware.py

FastAPI middleware stack:
1. CORSMiddleware       — Cross-origin request handling
2. RequestIDMiddleware  — Injects X-Request-ID header, binds to structlog context
3. TimingMiddleware     — Adds X-Process-Time header for performance monitoring
4. Global exception handlers — Converts AppError and unhandled exceptions to JSON

All middleware is registered in main.py via setup_middleware().
"""
from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from structlog.contextvars import bind_contextvars, clear_contextvars

from app.core.config import settings
from app.core.exceptions import AppError
from app.core.logging import get_logger

logger = get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Injects a unique X-Request-ID header into every request and response.

    The request ID is bound to the structlog context so every log line
    emitted during the request automatically includes the request_id field.
    This makes distributed tracing and log correlation trivial.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        # Clear any previous context (important for worker threads)
        clear_contextvars()

        # Use client-provided ID if present, otherwise generate one
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # Bind to structlog context — all loggers in this request see request_id
        bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class TimingMiddleware(BaseHTTPMiddleware):
    """
    Adds an X-Process-Time header to every response (in milliseconds).

    Also logs request completion with timing for performance analysis.
    Useful for identifying slow endpoints in production logs.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        response.headers["X-Process-Time"] = f"{duration_ms}ms"

        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        return response


def setup_middleware(app: FastAPI) -> None:
    """
    Register all middleware on the FastAPI application.

    Order matters: middleware is applied in reverse registration order.
    TimingMiddleware is registered first so it wraps everything (measures total time).
    """
    # 1. CORS — must be registered before other middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Process-Time"],
    )

    # 2. Request ID injection
    app.add_middleware(RequestIDMiddleware)

    # 3. Response timing
    app.add_middleware(TimingMiddleware)


def setup_exception_handlers(app: FastAPI) -> None:
    """
    Register global exception handlers that convert exceptions to JSON responses.

    These handlers catch exceptions that escape route handlers and middleware.
    """

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        """Convert all AppError subclasses to structured JSON responses."""
        logger.warning(
            "app_error",
            error_code=exc.error_code,
            message=exc.message,
            status_code=exc.status_code,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error_code": exc.error_code,
                "message": exc.message,
                "status_code": exc.status_code,
            },
        )

    @app.exception_handler(PydanticValidationError)
    async def pydantic_error_handler(
        request: Request,
        exc: PydanticValidationError,
    ) -> JSONResponse:
        """Convert Pydantic validation errors to structured JSON (422)."""
        return JSONResponse(
            status_code=422,
            content={
                "error_code": "validation_error",
                "message": "Request validation failed.",
                "status_code": 422,
                "errors": exc.errors(),
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """
        Catch-all handler for unexpected exceptions.

        Logs the full traceback but returns a generic message to the client
        to avoid leaking internal implementation details.
        """
        logger.exception(
            "unhandled_exception",
            path=request.url.path,
            method=request.method,
            error=str(exc),
        )
        return JSONResponse(
            status_code=500,
            content={
                "error_code": "internal_error",
                "message": "An unexpected error occurred.",
                "status_code": 500,
            },
        )
