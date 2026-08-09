"""
app/core/logging.py

Structured logging configuration using structlog.
Outputs JSON in production, colored text in development.
Every log record includes: timestamp, level, logger, request_id, and message.
"""
from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor

from app.core.config import settings


def _add_log_level(
    logger: Any,
    method: str,
    event_dict: EventDict,
) -> EventDict:
    """Add the log level name to every log record."""
    if method == "warn":
        method = "warning"
    event_dict["level"] = method.upper()
    return event_dict


def _drop_color_message_key(
    logger: Any,
    method: str,
    event_dict: EventDict,
) -> EventDict:
    """
    Remove uvicorn's color_message key to keep JSON clean.
    Uvicorn adds this for its own colored console output.
    """
    event_dict.pop("color_message", None)
    return event_dict


def configure_logging() -> None:
    """
    Configure structlog + stdlib logging.

    Called once at application startup from main.py lifespan.
    All libraries that use stdlib logging (uvicorn, sqlalchemy, celery)
    are captured and re-emitted through structlog's pipeline.
    """
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        _add_log_level,
        _drop_color_message_key,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.log_format == "json":
        # Production: structured JSON output
        renderer: Processor = structlog.processors.JSONRenderer()
    else:
        # Development: colored, human-readable console output
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # Apply to root logger — captures all stdlib logging output
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(settings.log_level)

    # Quiet verbose libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.DEBUG if settings.db_echo else logging.WARNING
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Return a named structlog logger.

    Usage:
        logger = get_logger(__name__)
        logger.info("user_created", user_id=str(user.id))
    """
    return structlog.get_logger(name)
