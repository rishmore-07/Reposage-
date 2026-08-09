"""
app/models/api_key.py

API key ORM model.

Security design:
- The raw key is NEVER stored in the database
- Only the SHA-256 hash of the key is stored (key_hash)
- The key prefix (first 8 chars) is stored for identification in the UI
- On creation: hash = SHA-256(raw_key); return raw_key once to user
- On validation: compute SHA-256(incoming) and look up key_hash
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import ApiKeyStatus
from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ApiKey(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    An API key for programmatic access to the RepoSage API.

    The raw key is returned once on creation and never stored.
    All subsequent lookups use the SHA-256 hash.
    """

    __tablename__ = "api_keys"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User who owns this API key",
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Human-readable name for the key (e.g., 'CI Pipeline')",
    )

    key_prefix: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        comment="First 8 characters of the raw key — shown in UI for identification",
    )

    key_hash: Mapped[str] = mapped_column(
        String(64),  # SHA-256 hex digest = 64 chars
        unique=True,
        index=True,
        nullable=False,
        comment="SHA-256 hash of the raw key — used for lookup and validation",
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ApiKeyStatus.ACTIVE,
        index=True,
        comment="Key lifecycle: active | revoked | expired",
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Optional expiry — null means the key never expires",
    )

    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of the last API request authenticated with this key",
    )

    def __repr__(self) -> str:
        return f"<ApiKey id={self.id} prefix={self.key_prefix!r} status={self.status!r}>"
