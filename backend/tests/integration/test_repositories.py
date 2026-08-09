import uuid

import httpx
import pytest
import respx
from httpx import AsyncClient, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import encrypt_string
from app.modules.repositories.models import Repository, UserConnectedRepository
from app.modules.users.models import User


@pytest.fixture
async def authenticated_user(test_db_session: AsyncSession):
    user = User(
        email="repo_user@example.com",
        full_name="Repo User",
        is_email_verified=True,
        github_id=123,
        github_username="repouser",
        github_access_token=encrypt_string("fake_github_token"),
    )
    test_db_session.add(user)
    await test_db_session.commit()
    return user


@pytest.fixture
async def second_user(test_db_session: AsyncSession):
    user = User(
        email="second_user@example.com",
        full_name="Second User",
        is_email_verified=True,
        github_id=456,
        github_username="seconduser",
        github_access_token=encrypt_string("fake_github_token_2"),
    )
    test_db_session.add(user)
    await test_db_session.commit()
    return user


@pytest.fixture
async def auth_client(client: AsyncClient, authenticated_user: User):
    from app.core.security import create_access_token
    token = create_access_token(subject=authenticated_user.id)
    client.cookies.set("access_token", token)
    return client


@pytest.fixture
async def second_auth_client(client: AsyncClient, second_user: User):
    from app.core.security import create_access_token
    token = create_access_token(subject=second_user.id)
    # create a new client to not share cookies
    async with AsyncClient(transport=client._transport, base_url="http://test") as ac:
        ac.cookies.set("access_token", token)
        yield ac


@pytest.fixture
def github_repo_mock_data():
    return {
        "id": 123456,
        "name": "test-repo",
        "full_name": "testuser/test-repo",
        "description": "A test repo",
        "private": False,
        "html_url": "https://github.com/testuser/test-repo",
        "clone_url": "https://github.com/testuser/test-repo.git",
        "ssh_url": "git@github.com:testuser/test-repo.git",
        "default_branch": "main",
        "owner": {
            "login": "testuser",
            "id": 999,
            "avatar_url": "https://avatars.githubusercontent.com/u/999"
        }
    }


# A. Unauthenticated repository discovery
@pytest.mark.asyncio
async def test_available_repositories_unauthenticated(client: AsyncClient):
    response = await client.get("/api/v1/repositories/available")
    assert response.status_code == 401


# B. Pagination
@pytest.mark.asyncio
@respx.mock
async def test_available_repositories_pagination(auth_client: AsyncClient):
    # Page 1
    respx.get("https://api.github.com/user/repos?type=all&sort=updated&page=1&per_page=20").mock(
        return_value=Response(200, json=[], headers={"link": '<https://api.github.com/user/repos?page=2>; rel="next"'})
    )
    # Page 2
    respx.get("https://api.github.com/user/repos?type=all&sort=updated&page=2&per_page=20").mock(
        return_value=Response(200, json=[])
    )

    r1 = await auth_client.get("/api/v1/repositories/available?page=1")
    assert r1.status_code == 200
    assert r1.json()["has_next"] is True

    r2 = await auth_client.get("/api/v1/repositories/available?page=2")
    assert r2.status_code == 200
    assert r2.json()["has_next"] is False


# C. Search
@pytest.mark.asyncio
@respx.mock
async def test_available_repositories_search(auth_client: AsyncClient):
    respx.get("https://api.github.com/search/repositories?q=react+in%3Aname%2Cdescription&page=1&per_page=20").mock(
        return_value=Response(200, json={"total_count": 1, "items": []})
    )
    response = await auth_client.get("/api/v1/repositories/available?q=react")
    assert response.status_code == 200
    assert response.json()["total_count"] == 1


# D. Cross-user repository access (403/404)
@pytest.mark.asyncio
@respx.mock
async def test_cross_user_access(
    auth_client: AsyncClient,
    second_auth_client: AsyncClient,
    github_repo_mock_data: dict
):
    repo_id = github_repo_mock_data["id"]
    respx.get(f"https://api.github.com/repositories/{repo_id}").mock(
        return_value=Response(200, json=github_repo_mock_data)
    )

    # User 1 connects repo
    response = await auth_client.post("/api/v1/repositories", json={"github_repo_id": repo_id, "organization_id": None})
    assert response.status_code == 201
    db_id = response.json()["id"]

    # User 2 tries to read repo
    response2 = await second_auth_client.get(f"/api/v1/repositories/{db_id}")
    assert response2.status_code == 403


# E. Cross-user disconnect
@pytest.mark.asyncio
@respx.mock
async def test_cross_user_disconnect(
    auth_client: AsyncClient,
    second_auth_client: AsyncClient,
    github_repo_mock_data: dict,
    test_db_session: AsyncSession
):
    repo_id = github_repo_mock_data["id"]
    respx.get(f"https://api.github.com/repositories/{repo_id}").mock(
        return_value=Response(200, json=github_repo_mock_data)
    )

    # User 1 connects repo
    response = await auth_client.post("/api/v1/repositories", json={"github_repo_id": repo_id, "organization_id": None})
    db_id = response.json()["id"]

    # User 2 tries to disconnect
    response2 = await second_auth_client.delete(f"/api/v1/repositories/{db_id}")
    assert response2.status_code == 403

    # Ensure connection still exists for User 1
    repo = await test_db_session.get(Repository, uuid.UUID(db_id))
    assert repo is not None


# F. Same repository connected by two users
@pytest.mark.asyncio
@respx.mock
async def test_same_repo_two_users(
    auth_client: AsyncClient,
    second_auth_client: AsyncClient,
    github_repo_mock_data: dict,
    test_db_session: AsyncSession
):
    repo_id = github_repo_mock_data["id"]
    respx.get(f"https://api.github.com/repositories/{repo_id}").mock(
        return_value=Response(200, json=github_repo_mock_data)
    )

    # User 1 connects
    await auth_client.post("/api/v1/repositories", json={"github_repo_id": repo_id, "organization_id": None})

    # User 2 connects
    await second_auth_client.post("/api/v1/repositories", json={"github_repo_id": repo_id, "organization_id": None})

    # Verify ONE global repo
    repo_count = await test_db_session.execute(select(func.count(Repository.id)))
    assert repo_count.scalar() == 1

    # Verify TWO connections
    conn_count = await test_db_session.execute(select(func.count(UserConnectedRepository.user_id)))
    assert conn_count.scalar() == 2


# G. Duplicate connection (Idempotent)
@pytest.mark.asyncio
@respx.mock
async def test_connect_repository_duplicate(auth_client: AsyncClient, github_repo_mock_data: dict):
    repo_id = github_repo_mock_data["id"]
    respx.get(f"https://api.github.com/repositories/{repo_id}").mock(
        return_value=Response(200, json=github_repo_mock_data)
    )
    payload = {"github_repo_id": repo_id, "organization_id": None}

    await auth_client.post("/api/v1/repositories", json=payload)
    response = await auth_client.post("/api/v1/repositories", json=payload)
    assert response.status_code == 201


# H. Invalid GitHub token
@pytest.mark.asyncio
@respx.mock
async def test_github_invalid_token_401(auth_client: AsyncClient):
    respx.get("https://api.github.com/user/repos?type=all&sort=updated&page=1&per_page=20").mock(
        return_value=Response(401, json={"message": "Bad credentials"})
    )
    response = await auth_client.get("/api/v1/repositories/available")
    assert response.status_code == 401
    assert "GitHub token is invalid" in response.json()["detail"]


# I. GitHub timeout
@pytest.mark.asyncio
@respx.mock
async def test_github_timeout(auth_client: AsyncClient):
    respx.get("https://api.github.com/user/repos?type=all&sort=updated&page=1&per_page=20").mock(
        side_effect=httpx.TimeoutException("Timeout")
    )
    response = await auth_client.get("/api/v1/repositories/available")
    assert response.status_code == 504
    assert "timed out" in response.json()["detail"].lower()


# J. GitHub 404 / inaccessible repository
@pytest.mark.asyncio
@respx.mock
async def test_github_404_not_found(auth_client: AsyncClient, test_db_session: AsyncSession):
    respx.get("https://api.github.com/repositories/99999").mock(
        return_value=Response(404, json={"message": "Not Found"})
    )
    response = await auth_client.post("/api/v1/repositories", json={"github_repo_id": 99999, "organization_id": None})
    assert response.status_code == 404

    # Ensure no db row created
    repo_count = await test_db_session.execute(select(func.count(Repository.id)))
    assert repo_count.scalar() == 0


# K. GitHub 403
@pytest.mark.asyncio
@respx.mock
async def test_github_403_forbidden(auth_client: AsyncClient):
    respx.get("https://api.github.com/user/repos?type=all&sort=updated&page=1&per_page=20").mock(
        return_value=Response(403, headers={"X-RateLimit-Remaining": "0"})
    )
    response = await auth_client.get("/api/v1/repositories/available")
    assert response.status_code == 429
    assert "rate limit" in response.json()["detail"].lower()

    respx.get("https://api.github.com/user/repos?type=all&sort=updated&page=1&per_page=20").mock(
        return_value=Response(403, headers={"X-RateLimit-Remaining": "50"})
    )
    response2 = await auth_client.get("/api/v1/repositories/available")
    assert response2.status_code == 403
    assert "forbidden" in response2.json()["detail"].lower()
