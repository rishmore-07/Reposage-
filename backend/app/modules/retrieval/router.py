"""
app/modules/retrieval/router.py

Search API router.

Exposes a single search endpoint supporting three retrieval modes:
- semantic: Vector search via Nomic embeddings + Qdrant
- keyword: BM25 lexical search
- hybrid: Combined via Reciprocal Rank Fusion (RRF)

The router is intentionally thin — all retrieval logic lives in
SearchService and its underlying retriever classes.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db
from app.core.logging import get_logger
from app.modules.users.models import User
from app.modules.repositories.models import UserConnectedRepository
from app.modules.retrieval.schemas import (
    SearchQueryRequest,
    SearchQueryResponse,
    SearchResult,
)
from app.modules.retrieval.search_service import SearchService

logger = get_logger(__name__)

router = APIRouter(prefix="/repositories/{repository_id}/search", tags=["search"])


@router.post("", response_model=SearchQueryResponse)
async def search_repository(
    repository_id: uuid.UUID,
    request: SearchQueryRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Search for code chunks within a specific repository.

    Supports three retrieval modes:
    - **semantic**: Vector similarity search using Nomic embeddings + Qdrant
    - **keyword**: BM25 lexical search for exact identifiers and terms
    - **hybrid**: Combines both via Reciprocal Rank Fusion (default)

    Set `debug=true` to include detailed ranking information from each
    retrieval system in the response.
    """
    # 1. Authorization: Ensure user has access to this repository
    result = await db.execute(
        select(UserConnectedRepository).where(
            UserConnectedRepository.user_id == current_user.id,
            UserConnectedRepository.repository_id == repository_id
        )
    )
    user_conn = result.scalar_one_or_none()
    if not user_conn:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to search this repository."
        )

    # 2. Perform search using the unified SearchService
    search_service = SearchService(db=db)
    try:
        response_data = await search_service.search(
            repository_id=repository_id,
            query=request.query,
            mode=request.mode,
            top_k=request.top_k,
            debug=request.debug,
        )
    except RuntimeError as e:
        logger.warning(
            "search_runtime_error",
            repository_id=str(repository_id),
            mode=request.mode,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "search_unexpected_error",
            repository_id=str(repository_id),
            mode=request.mode,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while searching: {e}"
        )

    # 3. Build response
    search_results = [
        SearchResult(**r) for r in response_data["results"]
    ]

    return SearchQueryResponse(
        results=search_results,
        mode=response_data["mode"],
        total_candidates=response_data.get("total_candidates", len(search_results)),
    )
