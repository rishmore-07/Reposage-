"""
Integration tests for Phase 3A ingestion API.
"""

import uuid
from httpx import AsyncClient
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

import pytest_asyncio
from fastapi import FastAPI
from app.main import create_app
from app.api.dependencies import get_current_user
from app.core.constants import IngestionStatus
from app.modules.repositories.models import Repository, RepositoryIngestion, UserConnectedRepository
from app.modules.users.models import User

@pytest_asyncio.fixture
async def test_user(test_db_session: AsyncSession) -> User:
    user = User(email="test@example.com", github_id=123)
    test_db_session.add(user)
    await test_db_session.commit()
    return user

@pytest_asyncio.fixture
async def test_repository(test_db_session: AsyncSession, test_user: User) -> Repository:
    repo = Repository(
        github_repo_id=456,
        full_name="test/repo",
        name="repo",
        html_url="http://github.com/test/repo",
        default_branch="main",
        is_private=False,
    )
    test_db_session.add(repo)
    await test_db_session.flush()
    
    conn = UserConnectedRepository(user_id=test_user.id, repository_id=repo.id)
    test_db_session.add(conn)
    
    await test_db_session.commit()
    return repo

@pytest_asyncio.fixture
async def auth_client(client: AsyncClient, test_user: User) -> AsyncClient:
    app = client._transport.app
    app.dependency_overrides[get_current_user] = lambda: test_user
    yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_start_ingestion_success(
    auth_client: AsyncClient,
    test_db_session: AsyncSession,
    test_user: User,
    test_repository: Repository,
):
    """Test starting a new ingestion job successfully."""
    response = await auth_client.post(f"/api/v1/repositories/{test_repository.id}/ingest")
    assert response.status_code == 201
    
    data = response.json()
    assert data["status"] == "pending"
    assert data["repository_id"] == str(test_repository.id)
    assert "id" in data
    
    # Verify in DB
    ingestion_id = uuid.UUID(data["id"])
    ingestion = await test_db_session.get(RepositoryIngestion, ingestion_id)
    assert ingestion is not None
    assert ingestion.status == IngestionStatus.PENDING

@pytest.mark.asyncio
async def test_start_ingestion_duplicate(
    auth_client: AsyncClient,
    test_db_session: AsyncSession,
    test_user: User,
    test_repository: Repository,
):
    """Test that starting ingestion twice returns the same active job."""
    res1 = await auth_client.post(f"/api/v1/repositories/{test_repository.id}/ingest")
    assert res1.status_code == 201
    id1 = res1.json()["id"]
    
    res2 = await auth_client.post(f"/api/v1/repositories/{test_repository.id}/ingest")
    assert res2.status_code == 201
    id2 = res2.json()["id"]
    
    assert id1 == id2, "Duplicate request should return the existing active job"

@pytest.mark.asyncio
async def test_get_ingestion_status(
    auth_client: AsyncClient,
    test_db_session: AsyncSession,
    test_user: User,
    test_repository: Repository,
):
    """Test polling the ingestion status."""
    # Start ingestion
    res1 = await auth_client.post(f"/api/v1/repositories/{test_repository.id}/ingest")
    ingestion_id = res1.json()["id"]
    
    # Get status
    res2 = await auth_client.get(f"/api/v1/repositories/{test_repository.id}/ingestion")
    assert res2.status_code == 200
    assert res2.json()["id"] == ingestion_id
    assert res2.json()["status"] == "pending"

@pytest.mark.asyncio
async def test_unauthorized_access(
    client: AsyncClient,  # Unauthenticated client
    test_repository: Repository,
):
    """Test unauthenticated users cannot start ingestion."""
    response = await client.post(f"/api/v1/repositories/{test_repository.id}/ingest")
    assert response.status_code == 401
