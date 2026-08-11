"""
app/api/v1/repositories/router.py

Repository endpoints:
- GET  /api/v1/repositories         — List current user's repositories
- POST /api/v1/repositories         — Connect a new repository
- GET  /api/v1/repositories/{id}    — Get a repository by ID
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db
from app.core.pagination import Page
from app.modules.github.schemas import GitHubRepositoryListResponse
from app.modules.repositories.schemas import RepositoryCreate, RepositoryRead, RepositoryIngestionRead
from app.modules.repositories.service import RepositoryService
from app.modules.repositories.ingestion_service import IngestionService
from app.modules.users.models import User

router = APIRouter()


def get_repository_service(db: AsyncSession = Depends(get_db)) -> RepositoryService:
    """Factory dependency for RepositoryService."""
    return RepositoryService(session=db)


def get_ingestion_service(db: AsyncSession = Depends(get_db)) -> IngestionService:
    """Factory dependency for IngestionService."""
    return IngestionService(session=db)


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


@router.get(
    "/available",
    response_model=GitHubRepositoryListResponse,
    summary="List available GitHub repositories",
    description="Returns repositories from GitHub that the current user has access to.",
)
async def list_available_repositories(
    q: str | None = None,
    page: int = 1,
    per_page: int = 20,
    current_user: User = Depends(get_current_user),
    service: RepositoryService = Depends(get_repository_service),
) -> GitHubRepositoryListResponse:
    return await service.list_available_repositories(
        current_user,
        query=q,
        page=page,
        per_page=per_page,
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
    import traceback
    try:
        repo = await service.connect_repository(data, current_user)
        return RepositoryRead.model_validate(repo)
    except Exception as exc:
        import logging
        logging.getLogger("app.repositories.router").error(
            f"connect_repository FAILED: {type(exc).__name__}: {exc}\n{traceback.format_exc()}"
        )
        raise


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


@router.delete(
    "/{repository_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Disconnect a repository",
    description="Removes the connection between the user and the repository.",
)
async def disconnect_repository(
    repository_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: RepositoryService = Depends(get_repository_service),
) -> None:
    await service.disconnect_repository(repository_id, current_user)


@router.post(
    "/{repository_id}/ingest",
    response_model=RepositoryIngestionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Start repository ingestion",
    description="Queues a background job to ingest the repository.",
)
async def start_ingestion(
    repository_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: IngestionService = Depends(get_ingestion_service),
) -> RepositoryIngestionRead:
    ingestion = await service.create_ingestion(repository_id, current_user)
    return RepositoryIngestionRead.model_validate(ingestion)


@router.get(
    "/{repository_id}/ingestion",
    response_model=RepositoryIngestionRead,
    summary="Get latest ingestion status",
    description="Returns the status of the most recent ingestion job.",
)
async def get_ingestion_status(
    repository_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: IngestionService = Depends(get_ingestion_service),
) -> RepositoryIngestionRead:
    from fastapi import HTTPException
    
    await service.verify_access(repository_id, current_user)
    ingestion = await service.get_latest_ingestion(repository_id)
    if not ingestion:
        raise HTTPException(status_code=404, detail="No ingestion found for this repository.")
    
    return RepositoryIngestionRead.model_validate(ingestion)
