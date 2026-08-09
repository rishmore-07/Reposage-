"""
app/api/v1/repositories/router.py

Repository endpoints:
- GET  /api/v1/repositories         — List current user's repositories
- POST /api/v1/repositories         — Connect a new repository
- GET  /api/v1/repositories/{id}    — Get a repository by ID
- POST /api/v1/repositories/{id}/analyze — Trigger analysis pipeline
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db
from app.modules.users.models import User
from app.core.schemas import MessageResponse
from app.core.pagination import Page
from app.modules.repositories.schemas import RepositoryCreate, RepositoryRead
from app.modules.repositories.service import RepositoryService

router = APIRouter()


def get_repository_service(db: AsyncSession = Depends(get_db)) -> RepositoryService:
    """Factory dependency for RepositoryService."""
    return RepositoryService(session=db)


@router.get(
    "",
    response_model=Page[RepositoryRead],
    summary="List repositories",
    description="Returns a paginated list of repositories connected by the current user.",
)
async def list_repositories(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    service: RepositoryService = Depends(get_repository_service),
) -> Page[RepositoryRead]:
    offset = (page - 1) * page_size
    repos = await service.list_user_repositories(
        current_user,
        offset=offset,
        limit=page_size,
    )
    repo_schemas = [RepositoryRead.model_validate(r) for r in repos]
    return Page(
        items=repo_schemas,
        total=len(repo_schemas),  # Full count requires a separate COUNT query
        page=page,
        page_size=page_size,
        pages=max(1, (len(repo_schemas) + page_size - 1) // page_size),
    )


@router.post(
    "",
    response_model=RepositoryRead,
    status_code=status.HTTP_201_CREATED,
    summary="Connect a repository",
    description="Registers a GitHub repository for analysis. Initial status is 'pending'.",
)
async def connect_repository(
    data: RepositoryCreate,
    current_user: User = Depends(get_current_user),
    service: RepositoryService = Depends(get_repository_service),
) -> RepositoryRead:
    repo = await service.connect_repository(data, current_user)
    return RepositoryRead.model_validate(repo)


@router.get(
    "/{repository_id}",
    response_model=RepositoryRead,
    summary="Get a repository",
    description="Returns details for a specific repository. Requires ownership.",
)
async def get_repository(
    repository_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: RepositoryService = Depends(get_repository_service),
) -> RepositoryRead:
    repo = await service.get_repository(repository_id, current_user)
    return RepositoryRead.model_validate(repo)


@router.post(
    "/{repository_id}/analyze",
    response_model=RepositoryRead,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger analysis pipeline",
    description=(
        "Queues the repository for AI analysis. Returns 202 Accepted immediately. "
        "Poll the repository status field to track progress."
    ),
)
async def trigger_analysis(
    repository_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: RepositoryService = Depends(get_repository_service),
) -> RepositoryRead:
    repo = await service.trigger_analysis(repository_id, current_user)
    return RepositoryRead.model_validate(repo)
