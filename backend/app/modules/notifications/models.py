"""
app/models/notification.py

Notification ORM model.

Notifications are fan-out messages sent to users when events occur
(analysis complete, member invited, drift detected, etc.).
Each notification has a type, payload (JSON), and a read status.
"""
from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import NotificationType
from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Notification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A notification delivered to a specific user."""

    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Recipient user",
    )

    notification_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Event type (e.g., 'analysis_complete', 'member_invited')",
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Short human-readable notification title",
    )

    body: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Optional longer notification message body",
    )

    # JSON payload for structured data (e.g., repository_id, org_id)
    # Stored as JSON string — use json.loads/dumps in application code
    payload: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="JSON-encoded structured data for the notification",
    )

    is_read: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        index=True,
        comment="False = unread notification",
    )

    def __repr__(self) -> str:
        return (
            f"<Notification id={self.id} "
            f"type={self.notification_type!r} read={self.is_read}>"
        )


class AuditLog(UUIDPrimaryKeyMixin, Base):
    """
    Immutable audit log entry.

    Design: AuditLog intentionally omits updated_at — audit entries are
    append-only and must never be modified after creation.
    created_at provides the event timestamp.
    """

    __tablename__ = "audit_logs"

    # Immutable creation timestamp
    from datetime import UTC, datetime
    from sqlalchemy import DateTime, func

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Immutable event timestamp (UTC)",
    )

    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="User who performed the action (null for system actions)",
    )

    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Action identifier (e.g., 'repo.connected', 'auth.login.failed')",
    )

    resource_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Type of the affected resource (e.g., 'repository', 'user')",
    )

    resource_id: Mapped[str | None] = mapped_column(
        String(36),  # UUID string
        nullable=True,
        index=True,
        comment="ID of the affected resource",
    )

    ip_address: Mapped[str | None] = mapped_column(
        String(45),  # IPv6 max length
        nullable=True,
        comment="Client IP address at the time of the action",
    )

    user_agent: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        comment="Client User-Agent header",
    )

    # JSON-encoded additional context
    metadata_json: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="JSON-encoded additional context for the audit event",
    )

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} action={self.action!r} actor={self.actor_id}>"
