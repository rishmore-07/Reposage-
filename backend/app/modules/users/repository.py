"""
app/repositories/user_repository.py

User-specific data access methods that extend BaseRepository.
"""

from __future__ import annotations

from sqlalchemy import select

from app.db.repository import BaseRepository
from app.modules.users.models import User


class UserRepository(BaseRepository[User]):
    """Data access layer for User records."""

    model = User

    async def get_by_email(self, email: str) -> User | None:
        """
        Look up a user by email address.

        Args:
            email: The email to search for (case-insensitive).

        Returns:
            The matching User or None if not found.
        """
        result = await self.session.execute(select(User).where(User.email == email.lower()))
        return result.scalar_one_or_none()

    async def get_by_github_id(self, github_id: int) -> User | None:
        """
        Look up a user by their GitHub user ID.

        Used during GitHub OAuth login to find or create an account.
        """
        result = await self.session.execute(select(User).where(User.github_id == github_id))
        return result.scalar_one_or_none()

    async def email_exists(self, email: str) -> bool:
        """Return True if any user has this email address."""
        user = await self.get_by_email(email)
        return user is not None
