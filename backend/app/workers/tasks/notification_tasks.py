"""
app/workers/tasks/notification_tasks.py

Celery tasks for delivering notifications to users.
"""

from __future__ import annotations

from celery.utils.log import get_task_logger

from app.workers.celery_app import celery_app

logger = get_task_logger(__name__)


@celery_app.task(
    name="app.workers.tasks.notification_tasks.send_email_notification",
    bind=True,
    max_retries=5,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def send_email_notification(
    self: object,
    user_id: str,
    subject: str,
    body: str,
    *,
    to_email: str,
) -> dict[str, str]:
    """
    Send a transactional email notification to a user.

    In the future, this will use the configured SMTP server or
    a transactional email provider (SendGrid, Resend, etc.).
    """
    logger.info(f"Sending email notification to {to_email}: {subject}")

    # Future: implement SMTP or API-based email sending
    # from app.core.config import settings
    # smtp_client.send(to=to_email, subject=subject, body=body)

    return {"status": "sent", "to": to_email, "subject": subject}


@celery_app.task(
    name="app.workers.tasks.notification_tasks.fan_out_notification",
    ignore_result=True,
)
def fan_out_notification(
    user_ids: list[str],
    notification_type: str,
    title: str,
    body: str | None = None,
    payload: dict | None = None,
) -> None:
    """
    Create in-app notification records for multiple users.

    Called after events like analysis completion or drift detection
    to notify all relevant users simultaneously.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from app.core.config import settings
    from app.modules.notifications.models import Notification

    logger.info(f"Fan-out notification: {notification_type} to {len(user_ids)} users")

    import json
    import uuid

    engine = create_engine(settings.database_sync_url, pool_pre_ping=True)
    with Session(engine) as session:
        notifications = [
            Notification(
                user_id=uuid.UUID(uid),
                notification_type=notification_type,
                title=title,
                body=body,
                payload=json.dumps(payload) if payload else None,
            )
            for uid in user_ids
        ]
        session.add_all(notifications)
        session.commit()

    logger.info(f"Created {len(notifications)} notification records")
