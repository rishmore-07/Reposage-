"""
app/workers/celery_app.py

Celery application factory.

Configuration principles:
- All broker/backend URLs come from settings (never hardcoded)
- Tasks use JSON serialization (safe, language-agnostic)
- Task modules are explicitly listed (no autodiscovery to prevent import side effects)
- Retry behavior is configured per-task, not globally
"""

from __future__ import annotations

from celery import Celery

from app.core.config import settings

# Create the Celery application
celery_app = Celery(
    "reposage",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# ── Celery configuration ───────────────────────────────────────────────────────
celery_app.conf.update(
    # Serialization
    task_serializer=settings.celery_task_serializer,
    result_serializer=settings.celery_result_serializer,
    accept_content=settings.celery_accept_content,
    # Timezone
    timezone=settings.celery_timezone,
    enable_utc=True,
    # Task behavior
    task_acks_late=True,  # Acknowledge only after task completes (safe retry on crash)
    task_reject_on_worker_lost=True,  # Re-queue if worker dies mid-task
    task_track_started=True,  # Allow monitoring of running tasks
    worker_prefetch_multiplier=1,  # One task per worker at a time (prevents memory bloat for long tasks)
    # Result expiry
    result_expires=3600,  # Keep results for 1 hour
    # Task discovery — explicit imports prevent circular import issues
    include=[
        "app.workers.tasks.repo_tasks",
        "app.workers.tasks.notification_tasks",
        "app.workers.tasks.ingestion_tasks",
    ],
)

# ── Periodic tasks (Celery Beat) ──────────────────────────────────────────────
from celery.schedules import crontab  # noqa: E402

celery_app.conf.beat_schedule = {
    # Check for stale repositories every hour
    "check-stale-repositories": {
        "task": "app.workers.tasks.repo_tasks.check_stale_repositories",
        "schedule": crontab(minute=0),  # Every hour at :00
    },
}
