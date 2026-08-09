"""
app/workers/tasks/repo_tasks.py

Celery tasks for repository lifecycle management.

Task design:
- Each task opens its own database session (not shared with the API process)
- Status is updated at each stage so the frontend can poll for progress
- Tasks use autoretry_for to handle transient failures (network issues, DB restarts)
- All DB operations use the synchronous SQLAlchemy session (Celery is sync)
"""
from __future__ import annotations

import uuid

from celery import shared_task
from celery.utils.log import get_task_logger
from sqlalchemy import create_engine, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import RepositoryStatus
from app.modules.repositories.models import Repository
from app.workers.celery_app import celery_app

logger = get_task_logger(__name__)

# Synchronous engine for Celery tasks (Celery is not async-compatible)
_sync_engine = create_engine(settings.database_sync_url, pool_pre_ping=True)


def _get_sync_session() -> Session:
    """Return a new synchronous SQLAlchemy session for task use."""
    return Session(_sync_engine)


def _update_repo_status(
    repo_id: str,
    status: RepositoryStatus,
    error: str | None = None,
    commit_sha: str | None = None,
) -> None:
    """Update repository status in the database."""
    with _get_sync_session() as session:
        values: dict = {"status": status}
        if error is not None:
            values["analysis_error"] = error
        if commit_sha is not None:
            values["last_commit_sha"] = commit_sha

        session.execute(
            update(Repository)
            .where(Repository.id == uuid.UUID(repo_id))
            .values(**values)
        )
        session.commit()


@celery_app.task(
    name="app.workers.tasks.repo_tasks.clone_repository",
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # Retry after 60 seconds
    autoretry_for=(Exception,),
    retry_backoff=True,       # Exponential backoff between retries
    retry_backoff_max=300,    # Max 5 minutes between retries
)
def clone_repository(self: object, repo_id: str) -> dict[str, str]:
    """
    Clone a repository and prepare it for analysis.

    This task is triggered by RepositoryService.trigger_analysis().
    It updates the repository status through the pipeline stages.

    In the future, this task will:
    1. Authenticate with GitHub using the installation token
    2. Clone the repository to a temporary directory
    3. Dispatch embed_repository task on success
    """
    logger.info(f"Starting clone for repository {repo_id}")

    try:
        # Mark as cloning
        _update_repo_status(repo_id, RepositoryStatus.CLONING)
        logger.info(f"Repository {repo_id} status: CLONING")

        # ── Future: actual git clone logic goes here ──────────────────────────
        # from app.github.client import GitHubClient
        # client = GitHubClient(...)
        # clone_path = client.clone(repo.html_url)
        # ─────────────────────────────────────────────────────────────────────

        # Mark as analyzing (placeholder — real work in AI milestone)
        _update_repo_status(repo_id, RepositoryStatus.ANALYZING)
        logger.info(f"Repository {repo_id} status: ANALYZING")

        # Mark as ready (will eventually dispatch embed task first)
        _update_repo_status(repo_id, RepositoryStatus.READY)
        logger.info(f"Repository {repo_id} analysis complete")

        return {"status": "success", "repo_id": repo_id}

    except Exception as exc:
        logger.error(f"Repository {repo_id} analysis failed: {exc}")
        _update_repo_status(repo_id, RepositoryStatus.FAILED, error=str(exc))
        raise


@celery_app.task(
    name="app.workers.tasks.repo_tasks.check_stale_repositories",
    ignore_result=True,
)
def check_stale_repositories() -> None:
    """
    Periodic task (runs hourly via Celery Beat) that detects stale repositories.

    A repository is considered stale when its last_commit_sha no longer
    matches the HEAD commit on the default branch. In the future, this
    task will compare against the GitHub API and re-queue analysis.
    """
    logger.info("Running stale repository check")

    with _get_sync_session() as session:
        ready_repos = (
            session.query(Repository)
            .filter(Repository.status == RepositoryStatus.READY)
            .all()
        )

    logger.info(f"Found {len(ready_repos)} repositories in READY state")

    # Future: for each repo, check GitHub API for new commits
    # If HEAD != last_commit_sha, update status to STALE and re-queue
