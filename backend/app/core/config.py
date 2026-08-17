"""
app/core/config.py

Application configuration loaded from environment variables via Pydantic Settings.
All configuration is centralized here — no hardcoded values anywhere else.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings sourced from environment variables.

    Pydantic Settings automatically reads from:
    1. Environment variables (highest priority)
    2. .env file in the project root
    3. Default values defined here (lowest priority)
    """

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore unknown env vars gracefully
    )

    # ── Application ───────────────────────────────────────────────────────────
    app_env: Literal["development", "staging", "production"] = "development"
    app_name: str = "RepoSage"
    app_version: str = "0.1.0"
    debug: bool = False

    # ── Security ──────────────────────────────────────────────────────────────
    secret_key: str = Field(..., min_length=32)
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = Field(
        default="postgresql+asyncpg://reposage:reposage@localhost:5432/reposage",
        description="Async SQLAlchemy DSN for AsyncSession",
    )
    database_sync_url: str = Field(
        default="postgresql+psycopg2://reposage:reposage@localhost:5432/reposage",
        description="Sync SQLAlchemy DSN for Alembic migrations",
    )
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30
    db_echo: bool = False  # Set True only for SQL query debugging

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── Celery ────────────────────────────────────────────────────────────────
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    celery_task_serializer: str = "json"
    celery_result_serializer: str = "json"
    celery_accept_content: list[str] = ["json"]
    celery_timezone: str = "UTC"

    # ── Workspace & Ingestion ─────────────────────────────────────────────────
    repository_workspace_root: str = "./data/repositories"
    max_file_size_bytes: int = 10485760       # 10 MB
    max_repository_size_bytes: int = 524288000 # 500 MB
    max_file_count: int = 10000
    max_directory_depth: int = 20

    # ── CORS ──────────────────────────────────────────────────────────────────
    cors_origins: list[str] | str = ["http://localhost:5173", "http://localhost:3000"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Allow CORS_ORIGINS to be a comma-separated string in .env files."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    # ── GitHub ────────────────────────────────────────────────────────────────
    github_app_id: str | None = None
    github_private_key: str | None = None
    github_webhook_secret: str | None = None
    github_client_id: str | None = None
    github_client_secret: str | None = None

    # ── Embeddings ────────────────────────────────────────────────────────────
    embedding_provider: Literal["ollama", "gemini"] = "ollama"
    embedding_model: str = "nomic-embed-text:latest"
    embedding_base_url: str = "http://localhost:11434"
    embedding_api_key: str | None = None
    embedding_dimension: int = 768
    embedding_batch_size: int = 32

    # ── Vector Store ──────────────────────────────────────────────────────────
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_collection: str = "code_chunks"

    # ── Search ────────────────────────────────────────────────────────────────
    search_mode: Literal["semantic", "keyword", "hybrid"] = "hybrid"
    semantic_candidate_k: int = 50
    keyword_candidate_k: int = 50
    hybrid_top_k: int = 10
    rrf_k: int = 60
    keyword_index_dir: str = "./data/keyword_indices"

    # ── Logging ───────────────────────────────────────────────────────────────
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: Literal["json", "text"] = "json"

    # ── Email ─────────────────────────────────────────────────────────────────
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    email_from: str = "noreply@reposage.dev"

    # ── Derived properties ────────────────────────────────────────────────────

    @property
    def is_production(self) -> bool:
        """True when running in production environment."""
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        """True when running in development environment."""
        return self.app_env == "development"

    @property
    def api_prefix(self) -> str:
        """Root API prefix for all versioned routes."""
        return "/api"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return the cached Settings singleton.

    Uses @lru_cache so the .env file is read exactly once at startup.
    In tests, call get_settings.cache_clear() before overriding env vars.
    """
    return Settings()


# Module-level convenience export
settings: Settings = get_settings()
