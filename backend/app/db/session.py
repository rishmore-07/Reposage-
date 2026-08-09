"""
app/db/session.py

Async SQLAlchemy engine and session factory.

Architecture decisions:
- AsyncSession is used throughout — no sync sessions in FastAPI routes
- Connection pooling is configured from settings (pool_size, max_overflow)
- Sessions are per-request, injected via FastAPI dependency (api/dependencies.py)
- This module never imports any app-level code to avoid circular imports
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# ── Engine ────────────────────────────────────────────────────────────────────

engine: AsyncEngine = create_async_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout,
    pool_pre_ping=True,    # Validate connections before use (handles DB restarts)
    echo=settings.db_echo, # Log SQL statements when DEBUG mode
    future=True,           # Use SQLAlchemy 2.0 API
)

# ── Session factory ───────────────────────────────────────────────────────────

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Don't expire objects after commit (avoids lazy-load on closed session)
    autocommit=False,
    autoflush=False,
)


# ── Dependency-injectable session ─────────────────────────────────────────────

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a per-request database session.

    Usage in a route:
        @router.get("/items")
        async def list_items(db: AsyncSession = Depends(get_db_session)):
            ...

    The session is automatically committed on success and rolled back on error.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
