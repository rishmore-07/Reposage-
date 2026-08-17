"""
app/models/repository.py

Repository ORM model.

A Repository represents a GitHub repository that a user or organization
has connected to RepoSage for analysis. The status field tracks where
the repository is in the analysis pipeline.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, Index, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import RepositoryStatus, IngestionStatus
from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class UserConnectedRepository(TimestampMixin, Base):
    """
    Association table linking Users to Repositories.
    Allows multiple users to connect the same underlying GitHub repository
    without duplicating the global repository state.
    """
    __tablename__ = "user_connected_repositories"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        primary_key=True,
    )

    def __repr__(self) -> str:
        return f"<UserConnectedRepository user_id={self.user_id} repository_id={self.repository_id}>"



class Repository(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A GitHub repository connected to RepoSage.

    Tracks the analysis pipeline status and stores metadata fetched
    from the GitHub API at connection time.
    """

    __tablename__ = "repositories"

    # ── Ownership ─────────────────────────────────────────────────────────────
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="Organization that owns this repository (null for personal repos)",
    )

    # ── GitHub Metadata ────────────────────────────────────────────────────────
    github_repo_id: Mapped[int] = mapped_column(
        nullable=False,
        unique=True,
        index=True,
        comment="GitHub repository ID (stable across renames)",
    )

    full_name: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        index=True,
        comment="GitHub full name: 'owner/repo' (e.g., 'acme-corp/api')",
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Repository name without owner prefix",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Repository description from GitHub",
    )

    html_url: Mapped[str] = mapped_column(
        String(2048),
        nullable=False,
        comment="GitHub web URL for the repository",
    )

    default_branch: Mapped[str] = mapped_column(
        String(255),
        default="main",
        nullable=False,
        comment="Default branch name (usually 'main' or 'master')",
    )

    is_private: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="True if the repository is private on GitHub",
    )

    index_version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        comment="Schema version for vector and BM25 indices",
    )

    # ── Analysis State ────────────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=RepositoryStatus.PENDING,
        index=True,
        comment="Current analysis pipeline status",
    )

    last_analyzed_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        comment="Timestamp of the last successful analysis completion",
    )

    analysis_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Error message from the last failed analysis attempt",
    )

    # ── Git Metadata ──────────────────────────────────────────────────────────
    last_commit_sha: Mapped[str | None] = mapped_column(
        String(40),
        nullable=True,
        comment="SHA of the commit used in the last analysis",
    )
    
    ingestions: Mapped[list["RepositoryIngestion"]] = relationship(
        "RepositoryIngestion",
        back_populates="repository",
        cascade="all, delete-orphan",
    )

    indexed_files: Mapped[list["IndexedFile"]] = relationship(
        "IndexedFile",
        back_populates="repository",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Repository id={self.id} full_name={self.full_name!r} status={self.status!r}>"


class RepositoryIngestion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    An ingestion job for a repository.
    Tracks the lifecycle of parsing, embedding, and indexing.
    """

    __tablename__ = "repository_ingestions"
    
    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=IngestionStatus.PENDING,
        index=True,
    )
    
    started_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        comment="Timestamp when the Celery worker actually started the job",
    )
    
    completed_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        comment="Timestamp when the job finished (success or failure)",
    )
    
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Safe error message if the job failed",
    )
    
    repository: Mapped["Repository"] = relationship(
        "Repository",
        back_populates="ingestions",
    )
    
    progress_message: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Current progress message of the ingestion",
    )
    
    # ── Ingestion Metrics ─────────────────────────────────────────────────────
    file_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    parsed_file_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    symbol_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unsupported_file_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    parse_error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    indexed_files: Mapped[list["IndexedFile"]] = relationship(
        "IndexedFile",
        back_populates="ingestion",
        cascade="all, delete-orphan",
    )
    
    # Concurrency Safety:
    # Only allow one active (PENDING or RUNNING) ingestion per repository at a time.
    __table_args__ = (
        Index(
            "ix_repo_ingestions_active_unique",
            "repository_id",
            unique=True,
            postgresql_where=status.in_([IngestionStatus.PENDING, IngestionStatus.RUNNING]),
        ),
    )
    
    def __repr__(self) -> str:
        return f"<RepositoryIngestion id={self.id} repo_id={self.repository_id} status={self.status!r}>"


class IndexedFile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Metadata for a single file discovered in a cloned repository.
    Used as the basis for code chunks and indexing in future phases.
    """

    __tablename__ = "indexed_files"

    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    ingestion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repository_ingestions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    relative_path: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        index=True,
        comment="Path relative to the repository root",
    )

    file_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Size of the file in bytes",
    )

    extension: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="File extension, including the dot (e.g., '.py'). Empty string if no extension.",
    )

    is_binary: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="True if detected as a binary file",
    )

    file_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="SHA-256 hash of the file content",
    )

    repository: Mapped["Repository"] = relationship(
        "Repository",
        back_populates="indexed_files",
    )

    ingestion: Mapped["RepositoryIngestion"] = relationship(
        "RepositoryIngestion",
        back_populates="indexed_files",
    )
    
    code_symbols: Mapped[list["CodeSymbol"]] = relationship(
        "CodeSymbol",
        back_populates="indexed_file",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index(
            "ix_indexed_files_ingestion_path_unique",
            "ingestion_id",
            "relative_path",
            unique=True,
        ),
    )

    def __repr__(self) -> str:
        return f"<IndexedFile id={self.id} path={self.relative_path!r} hash={self.file_hash[:8]}>"


class CodeSymbol(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Structured code symbol extracted via Tree-sitter AST parsing.
    Represents classes, functions, methods, imports, etc.
    """

    __tablename__ = "code_symbols"

    indexed_file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("indexed_files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    parent_symbol_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("code_symbols.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        index=True,
    )

    symbol_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    language: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    # ── Source Locations ──────────────────────────────────────────────────────
    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    start_column: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_column: Mapped[int] = mapped_column(Integer, nullable=False)
    
    start_byte: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_byte: Mapped[int | None] = mapped_column(Integer, nullable=True)

    signature: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Extracted signature (e.g. def func(args) -> Ret)",
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    indexed_file: Mapped["IndexedFile"] = relationship(
        "IndexedFile",
        back_populates="code_symbols",
    )
    
    parent: Mapped["CodeSymbol"] = relationship(
        "CodeSymbol",
        remote_side="CodeSymbol.id",
        back_populates="children",
    )
    
    children: Mapped[list["CodeSymbol"]] = relationship(
        "CodeSymbol",
        back_populates="parent",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<CodeSymbol id={self.id} name={self.name} type={self.symbol_type}>"


class CodeChunk(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A semantic chunk of code, ready to be embedded and indexed in Qdrant.
    It contains metadata linking back to the original file and symbol.
    """

    __tablename__ = "code_chunks"

    indexed_file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("indexed_files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    code_symbol_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("code_symbols.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    parent_chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("code_chunks.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="The actual text content to be embedded",
    )

    chunk_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="e.g., 'class', 'function', 'file', 'method'",
    )

    symbol_name: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Name of the semantic symbol, if applicable",
    )

    language: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)
    start_byte: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_byte: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # ── Structural Context ────────────────────────────────────────────────────
    class_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Name of the enclosing class or struct, if any",
    )
    parent_symbol: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Name of the immediate parent symbol, if any",
    )
    module_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Derived module/package name based on file path",
    )
    context_path: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        comment="Deterministic dot-separated path (e.g. ClassName.method_name)",
    )

    content_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="SHA-256 hash of the content to detect unchanged chunks during re-indexing",
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    indexed_file: Mapped["IndexedFile"] = relationship(
        "IndexedFile",
    )

    code_symbol: Mapped["CodeSymbol"] = relationship(
        "CodeSymbol",
    )

    parent_chunk: Mapped["CodeChunk"] = relationship(
        "CodeChunk",
        remote_side="CodeChunk.id",
    )

    def __repr__(self) -> str:
        return f"<CodeChunk id={self.id} type={self.chunk_type} file_id={self.indexed_file_id}>"
