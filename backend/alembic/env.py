"""
alembic/env.py

Alembic runtime environment configuration.

Key decisions:
1. Database URL is read from environment variables (not alembic.ini)
   to avoid hardcoding credentials in version-controlled files.
2. All models are imported here so Alembic can detect schema changes via autogenerate.
3. Async engine is used for online migrations (supports PostgreSQL asyncpg driver).
4. target_metadata enables `alembic revision --autogenerate` to diff the DB schema
   against the ORM models and generate migration scripts automatically.
"""
from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import settings

# ── Load alembic.ini logging config ──────────────────────────────────────────
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Import all models so their tables are registered on Base.metadata ─────────
# This is what enables --autogenerate to detect new/changed/removed tables.
from app.db.base import Base  # noqa: E402
from app.modules.api_keys.models import ApiKey
from app.modules.notifications.models import Notification
from app.modules.organizations.models import Organization
from app.modules.repositories.models import Repository
from app.modules.users.models import User

target_metadata = Base.metadata

# ── Override DB URL from environment (never read from alembic.ini) ───────────
# Using the SYNC URL because Alembic's connection is synchronous
config.set_main_option("sqlalchemy.url", settings.database_sync_url)


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode (generate SQL script without connecting to DB).

    Useful for previewing migrations or applying them manually.
    Usage: alembic upgrade head --sql > migration.sql
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,  # Detect column type changes
        compare_server_default=True,  # Detect server default changes
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations using an existing database connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode using an async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # No pooling for migration runs
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (connect to DB and apply changes)."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
