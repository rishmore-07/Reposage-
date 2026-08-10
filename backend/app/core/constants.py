"""
app/core/constants.py

Application-wide enums and string constants.
Centralizing these prevents magic strings scattered across the codebase.
All constants are typed (Enum or StrEnum) for IDE autocompletion and mypy.
"""

from __future__ import annotations

from enum import StrEnum


class Environment(StrEnum):
    """Deployment environment identifiers."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class TokenType(StrEnum):
    """JWT token type claim values."""

    ACCESS = "access"
    REFRESH = "refresh"


class UserRole(StrEnum):
    """User roles within an organization."""

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class RepositoryStatus(StrEnum):
    """Analysis pipeline status for a repository."""

    PENDING = "pending"  # Registered but not yet analyzed
    QUEUED = "queued"  # Queued for Celery worker
    CLONING = "cloning"  # Worker is cloning the repo
    ANALYZING = "analyzing"  # Worker is running analysis pipeline
    EMBEDDING = "embedding"  # Worker is building vector embeddings
    READY = "ready"  # Analysis complete and available
    FAILED = "failed"  # Analysis failed (see error field)
    STALE = "stale"  # Repo has new commits — re-analysis needed


class IngestionStatus(StrEnum):
    """Status of a background ingestion job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class NotificationType(StrEnum):
    """Notification event types."""

    ANALYSIS_COMPLETE = "analysis_complete"
    ANALYSIS_FAILED = "analysis_failed"
    MEMBER_INVITED = "member_invited"
    MEMBER_JOINED = "member_joined"
    DRIFT_DETECTED = "drift_detected"
    BILLING_ALERT = "billing_alert"
    WEBHOOK_RECEIVED = "webhook_received"


class ApiKeyStatus(StrEnum):
    """API key lifecycle states."""

    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


class AuditAction(StrEnum):
    """Audit log action identifiers — immutable record of what happened."""

    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    LOGIN_SUCCESS = "auth.login.success"
    LOGIN_FAILED = "auth.login.failed"
    LOGOUT = "auth.logout"
    TOKEN_REFRESHED = "auth.token.refreshed"
    ORG_CREATED = "org.created"
    ORG_UPDATED = "org.updated"
    ORG_DELETED = "org.deleted"
    MEMBER_INVITED = "org.member.invited"
    MEMBER_REMOVED = "org.member.removed"
    REPO_CONNECTED = "repo.connected"
    REPO_DISCONNECTED = "repo.disconnected"
    REPO_ANALYSIS_TRIGGERED = "repo.analysis.triggered"
    API_KEY_CREATED = "api_key.created"
    API_KEY_REVOKED = "api_key.revoked"


# ── Pagination defaults ───────────────────────────────────────────────────────

DEFAULT_PAGE_SIZE: int = 20
MAX_PAGE_SIZE: int = 100

# ── HTTP header names ─────────────────────────────────────────────────────────

HEADER_REQUEST_ID = "X-Request-ID"
HEADER_PROCESS_TIME = "X-Process-Time"
HEADER_API_KEY = "X-API-Key"

# ── Celery queue names ────────────────────────────────────────────────────────

QUEUE_DEFAULT = "default"
QUEUE_HIGH_PRIORITY = "high"
QUEUE_LOW_PRIORITY = "low"
QUEUE_AI = "ai"
