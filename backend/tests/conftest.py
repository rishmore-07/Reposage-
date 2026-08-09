"""
tests/conftest.py

Pytest fixtures shared across all tests.

Architecture:
- test_db_session: Creates an in-memory SQLite async session for unit tests
  (no PostgreSQL required). SQLite is structurally compatible with our models.
- client: An AsyncClient wrapping the FastAPI app for integration tests.
- All fixtures use function scope (fresh state per test) by default.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.session import get_db_session
from app.main import create_app

# Import all models so they register on Base.metadata before create_all
import app.modules.users.models  # noqa
import app.modules.organizations.models  # noqa
import app.modules.repositories.models  # noqa
# In-memory SQLite for tests — no PostgreSQL required
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create a fresh async engine backed by in-memory SQLite."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a fresh database session per test.

    Rolls back all changes after each test so tests are isolated.
    """
    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def client(test_db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Provide an AsyncClient configured to use the test database.

    Overrides the get_db_session dependency so all test requests
    use the isolated test database, not the real PostgreSQL instance.
    """
    app = create_app()

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield test_db_session

    app.dependency_overrides[get_db_session] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
