"""
app/services/repository_service.py

Repository management service: connect, list, trigger analysis.
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import PermissionDeniedError, RepositoryNotFoundError
from app.core.logging import get_logger
from app.modules.repositories.models import Repository
from app.modules.users.models import User
from app.modules.repositories.repository import RepositoryRepository
from app.modules.repositories.schemas import RepositoryCreate, RepositoryRead, RepositoryStatusUpdate

logger = get_logger(__name__)


class RepositoryService:
    """Handles repository lifecycle: connection, status tracking, analysis trigger."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo_repo = RepositoryRepository(session)

    async def connect_repository(
        self,
        data: RepositoryCreate,
        current_user: User,
    ) -> Repository:
        """
        Register a new repository for analysis.

        The repository is created with PENDING status. The analysis pipeline
        is triggered separately via trigger_analysis().
        """
        repo = await self.repo_repo.create(
            owner_id=current_user.id,
            organization_id=data.organization_id,
            github_repo_id=data.github_repo_id,
            full_name=data.full_name,
            name=data.name,
            description=data.description,
            html_url=str(data.html_url),
            default_branch=data.default_branch,
            is_private=data.is_private,
        )

        logger.info(
            "repository_connected",
            repo_id=str(repo.id),
            full_name=repo.full_name,
            user_id=str(current_user.id),
        )
        return repo

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

        if repo.owner_id != current_user.id and not current_user.is_superuser:
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

    async def trigger_analysis(
        self,
        repo_id: uuid.UUID,
        current_user: User,
    ) -> Repository:
        """
        Queue the repository for analysis via Celery.

        Updates status to QUEUED and dispatches a Celery task.
        Returns 202 Accepted immediately — the analysis runs asynchronously.
        """
        from app.core.constants import RepositoryStatus
        from app.workers.celery_app import celery_app

        repo = await self.get_repository(repo_id, current_user)
        repo = await self.repo_repo.update(repo, status=RepositoryStatus.QUEUED)

        # Dispatch to Celery — non-blocking
        celery_app.send_task(
            "app.workers.tasks.repo_tasks.clone_repository",
            args=[str(repo.id)],
            queue="default",
        )

        logger.info(
            "analysis_triggered",
            repo_id=str(repo.id),
            full_name=repo.full_name,
        )
        return repo
