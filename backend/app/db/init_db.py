"""
app/db/init_db.py

Database initialization utilities called during application startup.

This module:
1. Tests the database connection
2. Logs the connection status
3. Does NOT call Base.metadata.create_all() — that is Alembic's job

In production, always use `alembic upgrade head` to apply schema changes.
"""
from __future__ import annotations

from sqlalchemy import text

from app.core.logging import get_logger
from app.db.session import engine

logger = get_logger(__name__)


async def check_db_connection() -> bool:
    """
    Verify that the database is reachable by executing a simple query.

    Returns:
        True if the connection succeeds, False otherwise.

    Called during the FastAPI lifespan startup event.
    """
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("database_connection_ok")
        return True
    except Exception as exc:
        logger.error("database_connection_failed", error=str(exc))
        return False


async def dispose_engine() -> None:
    """
    Dispose the SQLAlchemy engine connection pool.

    Called during FastAPI lifespan shutdown to gracefully close all
    database connections before the process exits.
    """
    await engine.dispose()
    logger.info("database_engine_disposed")
