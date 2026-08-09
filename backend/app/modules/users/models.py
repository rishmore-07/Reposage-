"""
app/models/user.py

User ORM model.

Design decisions:
- hashed_password is nullable to support OAuth-only accounts (GitHub login)
- is_active flag for soft account deactivation without data deletion
- is_superuser flag for internal admin access
- github_id for linking to GitHub OAuth accounts
"""
from __future__ import annotations

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Represents an authenticated user account."""

    __tablename__ = "users"

    # ── Identity ──────────────────────────────────────────────────────────────
    email: Mapped[str] = mapped_column(
        String(320),   # RFC 5321 max email length
        unique=True,
        index=True,
        nullable=False,
        comment="User's email address — must be unique",
    )

    full_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="User's display name",
    )

    avatar_url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
        comment="URL to the user's profile picture",
    )

    # ── Authentication ────────────────────────────────────────────────────────
    hashed_password: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,  # Nullable for OAuth-only accounts
        comment="bcrypt hash — null for OAuth-only accounts",
    )

    # ── GitHub OAuth ──────────────────────────────────────────────────────────
    github_id: Mapped[int | None] = mapped_column(
        nullable=True,
        unique=True,
        index=True,
        comment="GitHub user ID for OAuth account linking",
    )

    github_username: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="GitHub username (login)",
    )

    # ── Status flags ──────────────────────────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="False = soft-deleted or suspended account",
    )

    is_email_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="True once the user verifies their email address",
    )

    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="True for internal admin accounts only",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"
