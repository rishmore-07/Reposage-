"""
app/services/repository_service.py

Repository management service: connect, list, trigger analysis.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import PermissionDeniedError, RepositoryNotFoundError
from app.core.logging import get_logger
from app.modules.github.schemas import GitHubRepositoryListResponse
from app.modules.github.service import GitHubService
from app.modules.repositories.models import Repository
from app.modules.repositories.repository import RepositoryRepository
from app.modules.repositories.schemas import (
    RepositoryCreate,
)
from app.modules.users.models import User

logger = get_logger(__name__)


class RepositoryService:
    """Handles repository lifecycle: connection, status tracking, analysis trigger."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo_repo = RepositoryRepository(session)

    async def list_available_repositories(
        self,
        current_user: User,
        query: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> GitHubRepositoryListResponse:
        """List repositories available for the user to connect to."""
        github_service = GitHubService(current_user)
        return await github_service.get_available_repositories(query=query, page=page, per_page=per_page)

    async def connect_repository(
        self,
        data: RepositoryCreate,
        current_user: User,
    ) -> Repository:
        """
        Register a new repository for analysis.
        Verifies access via GitHub API first.
        """
        github_service = GitHubService(current_user)

        # 1. Fetch and verify from GitHub
        github_metadata = await github_service.get_repository_metadata(data.github_repo_id)

        # 2. Check if global Repository exists
        repo = await self.repo_repo.get_by_github_id(data.github_repo_id)

        if not repo:
            # Create global repository
            repo = await self.repo_repo.create(
                organization_id=data.organization_id,
                github_repo_id=github_metadata.id,
                full_name=github_metadata.full_name,
                name=github_metadata.name,
                description=github_metadata.description,
                html_url=github_metadata.html_url,
                default_branch=github_metadata.default_branch,
                is_private=github_metadata.private,
            )

        # 3. Create user connection if not exists
        conn = await self.repo_repo.get_connection(current_user.id, repo.id)
        if not conn:
            await self.repo_repo.create_connection(current_user.id, repo.id)

        await self.session.commit()

        logger.info(
            "repository_connected",
            repo_id=str(repo.id),
            full_name=repo.full_name,
            user_id=str(current_user.id),
        )
        return repo

    async def disconnect_repository(
        self,
        repo_id: uuid.UUID,
        current_user: User,
    ) -> None:
        """Disconnect a repository for the current user."""
        repo = await self.repo_repo.get_by_id(repo_id)
        if not repo:
            raise RepositoryNotFoundError()

        conn = await self.repo_repo.get_connection(current_user.id, repo.id)
        if not conn:
            raise PermissionDeniedError()

        await self.repo_repo.delete_connection(current_user.id, repo.id)
        await self.session.commit()

        logger.info(
            "repository_disconnected",
            repo_id=str(repo.id),
            full_name=repo.full_name,
            user_id=str(current_user.id),
        )

    async def get_repository(
        self,
        repo_id: uuid.UUID,
        current_user: User,
    ) -> Repository:
        """
        Fetch a repository by ID, verifying the user has access.

        Raises RepositoryNotFoundError if not found.
        Raises PermissionDeniedError if the user doesn't own it.
        """
        repo = await self.repo_repo.get_by_id(repo_id)
        if repo is None:
            raise RepositoryNotFoundError()

        if not current_user.is_superuser:
            conn = await self.repo_repo.get_connection(current_user.id, repo.id)
            if not conn:
                raise PermissionDeniedError()

        return repo

    async def list_user_repositories(
        self,
        current_user: User,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Repository]:
        """Return paginated repositories owned by the current user."""
        return await self.repo_repo.get_by_owner(
            current_user.id,
            offset=offset,
            limit=limit,
        )


