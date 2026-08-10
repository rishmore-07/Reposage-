"""
app/modules/repositories/ingestion_service.py

Service for managing repository ingestion jobs.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, exc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import IngestionStatus
from app.core.exceptions import RepositoryNotFoundError, PermissionDeniedError
from app.core.logging import get_logger
from app.modules.repositories.models import RepositoryIngestion
from app.modules.repositories.service import RepositoryService
from app.modules.users.models import User
from app.workers.tasks.ingestion_tasks import ingest_repository

logger = get_logger(__name__)


class IngestionService:
    """Handles the lifecycle of repository ingestion jobs."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo_service = RepositoryService(session)

    async def verify_access(self, repository_id: uuid.UUID, current_user: User) -> None:
        """Verify the user has access to the repository."""
        # This will raise exceptions if access is denied or repo is not found
        await self.repo_service.get_repository(repository_id, current_user)

    async def get_active_ingestion(self, repository_id: uuid.UUID) -> RepositoryIngestion | None:
        """Return the active ingestion job if one exists."""
        stmt = select(RepositoryIngestion).where(
            RepositoryIngestion.repository_id == repository_id,
            RepositoryIngestion.status.in_([IngestionStatus.PENDING, IngestionStatus.RUNNING]),
        )
        return await self.session.scalar(stmt)

    async def get_latest_ingestion(self, repository_id: uuid.UUID) -> RepositoryIngestion | None:
        """Return the most recent ingestion job."""
        stmt = (
            select(RepositoryIngestion)
            .where(RepositoryIngestion.repository_id == repository_id)
            .order_by(RepositoryIngestion.created_at.desc())
            .limit(1)
        )
        return await self.session.scalar(stmt)

    async def create_ingestion(self, repository_id: uuid.UUID, current_user: User) -> RepositoryIngestion:
        """
        Create a new ingestion job or return the existing active one.
        Queues the Celery task safely.
        """
        # 1. Authorize
        await self.verify_access(repository_id, current_user)

        # 2. Check for existing active job (optimistic)
        active = await self.get_active_ingestion(repository_id)
        if active:
            return active

        # 3. Create new job
        ingestion = RepositoryIngestion(
            repository_id=repository_id,
            status=IngestionStatus.PENDING,
        )
        self.session.add(ingestion)
        
        try:
            # We must commit to trigger DB-level unique constraint
            await self.session.commit()
            await self.session.refresh(ingestion)
        except exc.IntegrityError:
            # Caught a concurrent insert violation! 
            # Another request beat us to creating an active ingestion.
            await self.session.rollback()
            active = await self.get_active_ingestion(repository_id)
            if active:
                return active
            # Fallback if somehow it's not active anymore but we got IntegrityError
            raise

        logger.info(f"Created ingestion {ingestion.id} for repository {repository_id}")

        # 4. Dispatch Celery task
        try:
            # Pass ONLY the string identifier, no tokens or objects
            ingest_repository.delay(str(ingestion.id))
            logger.info(f"Queued Celery task for ingestion {ingestion.id}")
        except Exception as e:
            # If Celery is down or dispatch fails, don't leave it permanently PENDING
            logger.error(f"Failed to queue Celery task for ingestion {ingestion.id}: {e}")
            ingestion.status = IngestionStatus.FAILED
            ingestion.error_message = "Failed to dispatch background task."
            ingestion.completed_at = datetime.now(UTC)
            self.session.add(ingestion)
            await self.session.commit()
            await self.session.refresh(ingestion)

        return ingestion
