"""
app/repositories/repository_repository.py

Repository-specific data access methods.
(Yes, 'repository_repository' — the domain object is "Repository",
 the pattern is "repository". The naming is intentional.)
"""

from __future__ import annotations

import uuid

from sqlalchemy import delete, select

from app.db.repository import BaseRepository
from app.modules.repositories.models import Repository, UserConnectedRepository


class RepositoryRepository(BaseRepository[Repository]):
    """Data access layer for Repository records."""

    model = Repository

    async def get_by_github_id(self, github_repo_id: int) -> Repository | None:
        """
        Look up a repository by its stable GitHub repository ID.

        GitHub repo IDs don't change when a repo is renamed or transferred,
        making them more reliable than full_name for lookups.
        """
        result = await self.session.execute(
            select(Repository).where(Repository.github_repo_id == github_repo_id)
        )
        return result.scalar_one_or_none()

    async def get_by_owner(
        self,
        owner_id: uuid.UUID,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Repository]:
        """Return paginated repositories connected by a specific user."""
        result = await self.session.execute(
            select(Repository)
            .join(UserConnectedRepository, UserConnectedRepository.repository_id == Repository.id)
            .where(UserConnectedRepository.user_id == owner_id)
            .order_by(Repository.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_connection(self, user_id: uuid.UUID, repository_id: uuid.UUID) -> UserConnectedRepository | None:
        """Fetch a connection between a user and a repository."""
        result = await self.session.execute(
            select(UserConnectedRepository)
            .where(UserConnectedRepository.user_id == user_id, UserConnectedRepository.repository_id == repository_id)
        )
        return result.scalar_one_or_none()

    async def create_connection(self, user_id: uuid.UUID, repository_id: uuid.UUID) -> UserConnectedRepository:
        """Create a connection between a user and a repository."""
        conn = UserConnectedRepository(user_id=user_id, repository_id=repository_id)
        self.session.add(conn)
        await self.session.flush()
        return conn

    async def delete_connection(self, user_id: uuid.UUID, repository_id: uuid.UUID) -> None:
        """Delete a connection between a user and a repository."""
        await self.session.execute(
            delete(UserConnectedRepository)
            .where(UserConnectedRepository.user_id == user_id, UserConnectedRepository.repository_id == repository_id)
        )
        await self.session.flush()

    async def get_by_organization(
        self,
        organization_id: uuid.UUID,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Repository]:
        """Return paginated repositories belonging to an organization."""
        result = await self.session.execute(
            select(Repository)
            .where(Repository.organization_id == organization_id)
            .order_by(Repository.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_status(self, status: str) -> list[Repository]:
        """
        Return all repositories with a given analysis status.

        Used by monitoring and recovery scripts to find stuck jobs.
        """
        result = await self.session.execute(select(Repository).where(Repository.status == status))
        return list(result.scalars().all())
