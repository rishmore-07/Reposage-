"""
app/schemas/repository.py

Pydantic v2 schemas for repository endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.core.constants import RepositoryStatus


class RepositoryRead(BaseModel):
    """Schema returned by the API for repository data."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    organization_id: uuid.UUID | None
    github_repo_id: int
    full_name: str
    name: str
    description: str | None
    html_url: str
    default_branch: str
    is_private: bool
    status: str
    last_analyzed_at: datetime | None
    analysis_error: str | None
    last_commit_sha: str | None
    created_at: datetime
    updated_at: datetime


class RepositoryCreate(BaseModel):
    """Request body for connecting a new repository."""

    github_repo_id: int = Field(..., description="GitHub repository ID")
    organization_id: uuid.UUID | None = Field(
        None,
        description="Organization to connect under (null for personal repos)",
    )


class RepositoryStatusUpdate(BaseModel):
    """Internal schema used by Celery workers to update analysis status."""

    status: RepositoryStatus
    analysis_error: str | None = None
    last_commit_sha: str | None = None
