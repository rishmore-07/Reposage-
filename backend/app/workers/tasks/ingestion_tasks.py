"""
app/workers/tasks/ingestion_tasks.py

Celery tasks for repository ingestion (Phase 3).
"""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime

from celery.utils.log import get_task_logger
from sqlalchemy import create_engine, update, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import IngestionStatus
from app.core.encryption import decrypt_string
from app.modules.repositories.models import (
    RepositoryIngestion,
    Repository,
    UserConnectedRepository,
    IndexedFile
)
from app.modules.users.models import User
from app.modules.repositories.git_service import GitRepositoryService
from app.modules.repositories.file_discovery import FileDiscoveryService
from app.workers.celery_app import celery_app

logger = get_task_logger(__name__)

# Synchronous engine for Celery tasks (Celery is not async-compatible)
_sync_engine = create_engine(settings.database_sync_url, pool_pre_ping=True)


def _get_sync_session() -> Session:
    """Return a new synchronous SQLAlchemy session for task use."""
    return Session(_sync_engine)


@celery_app.task(
    name="app.workers.tasks.ingestion_tasks.ingest_repository",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
)
def ingest_repository(self: object, ingestion_id: str) -> dict[str, str]:
    """
    Background job to ingest a repository (Phase 3B).
    Clones the repository and discovers files safely.
    """
    logger.info(f"Starting ingestion job {ingestion_id}")

    # To ensure cleanup runs even on unexpected Celery failures, we keep track of the git service
    git_service = None

    try:
        with _get_sync_session() as session:
            # 1. Fetch the ingestion record and associated repository
            ingestion = session.scalar(
                select(RepositoryIngestion).where(RepositoryIngestion.id == uuid.UUID(ingestion_id))
            )
            
            if not ingestion:
                logger.error(f"Ingestion record {ingestion_id} not found.")
                return {"status": "error", "message": "Record not found"}
                
            repository = session.scalar(
                select(Repository).where(Repository.id == ingestion.repository_id)
            )

            # Find a user connected to this repository to obtain credentials
            # In a real app we might want the specific user who triggered this,
            # but any connected user with a valid token works for cloning.
            user_conn = session.scalar(
                select(UserConnectedRepository).where(UserConnectedRepository.repository_id == repository.id)
            )
            
            if not user_conn:
                raise RuntimeError("No user is connected to this repository. Cannot authenticate.")
                
            user = session.scalar(
                select(User).where(User.id == user_conn.user_id)
            )
            
            if not user or not user.github_access_token:
                raise RuntimeError("Connected user does not have a GitHub access token.")

            # 2. Mark as RUNNING and "Cloning"
            ingestion.status = IngestionStatus.RUNNING
            ingestion.started_at = datetime.now(UTC)
            ingestion.progress_message = "Cloning repository"
            session.commit()
            
            # Secure token decryption (in memory only)
            github_token = decrypt_string(user.github_access_token)

            git_service = GitRepositoryService(repository.id, ingestion.id)
            
        # We perform time-consuming I/O outside the DB transaction
        # 3. Clone Repository
        commit_sha = git_service.clone_repository(
            full_name=repository.full_name,
            default_branch=repository.default_branch,
            github_token=github_token
        )
        
        # Discard token from local scope
        del github_token

        with _get_sync_session() as session:
            ingestion = session.scalar(
                select(RepositoryIngestion).where(RepositoryIngestion.id == uuid.UUID(ingestion_id))
            )
            ingestion.progress_message = "Discovering files"
            repository = session.scalar(
                select(Repository).where(Repository.id == ingestion.repository_id)
            )
            repository.last_commit_sha = commit_sha
            session.commit()

        # 4. Discover Files
        discovery_service = FileDiscoveryService(git_service.get_source_dir())
        discovered_files = discovery_service.discover_files()

        with _get_sync_session() as session:
            ingestion = session.scalar(
                select(RepositoryIngestion).where(RepositoryIngestion.id == uuid.UUID(ingestion_id))
            )
            ingestion.progress_message = "Saving file metadata"
            session.commit()
            
            # 5. Batch insert IndexedFile records
            indexed_files_to_insert = [
                IndexedFile(
                    repository_id=repository.id,
                    ingestion_id=ingestion.id,
                    relative_path=f["relative_path"],
                    file_size=f["file_size"],
                    extension=f["extension"],
                    is_binary=f["is_binary"],
                    file_hash=f["file_hash"],
                )
                for f in discovered_files
            ]
            
            if indexed_files_to_insert:
                session.add_all(indexed_files_to_insert)
                
            ingestion.status = IngestionStatus.COMPLETED
            ingestion.progress_message = "Completed"
            ingestion.completed_at = datetime.now(UTC)
            session.commit()
            
            logger.info(f"Ingestion {ingestion_id} status: COMPLETED. Discovered {len(discovered_files)} files.")

        return {"status": "success", "ingestion_id": ingestion_id, "files_discovered": len(discovered_files)}

    except Exception as exc:
        logger.error(f"Ingestion job {ingestion_id} failed: {exc}")
        
        # Cleanup workspace on failure
        if git_service:
            try:
                git_service.cleanup_workspace()
            except Exception as cleanup_exc:
                logger.error(f"Failed to cleanup workspace: {cleanup_exc}")

        with _get_sync_session() as session:
            session.execute(
                update(RepositoryIngestion)
                .where(RepositoryIngestion.id == uuid.UUID(ingestion_id))
                .values(
                    status=IngestionStatus.FAILED,
                    progress_message="Failed",
                    error_message=str(exc),
                    completed_at=datetime.now(UTC)
                )
            )
            session.commit()
        raise
