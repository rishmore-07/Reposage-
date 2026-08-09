"""
app/models/repository.py

Repository ORM model.

A Repository represents a GitHub repository that a user or organization
has connected to RepoSage for analysis. The status field tracks where
the repository is in the analysis pipeline.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import RepositoryStatus
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
        ForeignKey("organizations.id", ondelete="CASCADE"),
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

    # ── Analysis State ────────────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=RepositoryStatus.PENDING,
        index=True,
        comment="Current analysis pipeline status",
    )

    last_analyzed_at: Mapped[uuid.UUID | None] = mapped_column(
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

    def __repr__(self) -> str:
        return f"<Repository id={self.id} full_name={self.full_name!r} status={self.status!r}>"
