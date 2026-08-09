"""
app/models/base.py

Shared SQLAlchemy mixins for all ORM models.

TimestampMixin — adds created_at and updated_at columns
UUIDPrimaryKeyMixin — uses UUID v4 as primary key (not auto-increment integer)

Using UUID primary keys:
- Safe to expose in URLs (no enumeration attacks)
- Compatible with distributed inserts across shards
- Globally unique across all tables (useful for audit logs)
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class UUIDPrimaryKeyMixin:
    """
    Adds a UUID v4 primary key column.

    The default is generated at the Python level (not DB level) so the ID
    is known before the INSERT, enabling optimistic inserts and pre-computed
    relationships without a DB round-trip.
    """

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        comment="Primary key — UUID v4 generated at insert time",
    )


class TimestampMixin:
    """
    Adds created_at and updated_at columns to any model.

    - created_at: Set once at INSERT time via server_default
    - updated_at: Set at INSERT and updated on every UPDATE via onupdate
    Both are timezone-aware (UTC) datetime objects.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Timestamp when the record was created (UTC)",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Timestamp when the record was last updated (UTC)",
    )
