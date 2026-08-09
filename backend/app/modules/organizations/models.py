"""
app/models/organization.py

Organization and OrganizationMembership ORM models.

An Organization is a container for users and repositories.
OrganizationMembership is the join table that links users to organizations
with a role (owner, admin, member, viewer).
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import UserRole
from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Organization(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A team or company account that owns repositories and members.
    Users can belong to multiple organizations with different roles.
    """

    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Display name of the organization",
    )

    slug: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
        comment="URL-safe identifier (e.g., 'acme-corp')",
    )

    description: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
        comment="Optional description of the organization",
    )

    avatar_url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
        comment="Organization profile picture URL",
    )

    # GitHub organization ID (for GitHub App integration)
    github_org_id: Mapped[int | None] = mapped_column(
        nullable=True,
        unique=True,
        index=True,
        comment="GitHub organization ID for webhook routing",
    )

    def __repr__(self) -> str:
        return f"<Organization id={self.id} slug={self.slug!r}>"


class OrganizationMembership(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Membership record linking a User to an Organization with a role.

    The unique constraint on (organization_id, user_id) ensures a user
    can only have one role per organization.
    """

    __tablename__ = "organization_memberships"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_org_user_membership"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to organizations",
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to users",
    )

    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=UserRole.MEMBER,
        comment="Member's role: owner | admin | member | viewer",
    )

    # Invitation tracking
    invited_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who sent the invitation",
    )

    def __repr__(self) -> str:
        return (
            f"<OrganizationMembership "
            f"org={self.organization_id} user={self.user_id} role={self.role!r}>"
        )
