import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.modules.users.models import User


@pytest.fixture
async def existing_user(test_db_session: AsyncSession):
    user = User(
        email="existing@example.com",
        full_name="Existing User",
        hashed_password=hash_password("password123"),
        is_email_verified=True,
    )
    test_db_session.add(user)
    await test_db_session.commit()
    return user


@pytest.mark.asyncio
async def test_register_new_user(client: AsyncClient, test_db_session: AsyncSession):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "securepassword",
            "full_name": "New User",
        },
    )
    assert response.status_code == 201
    assert "access_token" in response.cookies
    assert "refresh_token" in response.cookies


@pytest.mark.asyncio
async def test_register_existing_user(client: AsyncClient, existing_user: User):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "existing@example.com",
            "password": "newpassword123",
            "full_name": "Another User",
        },
    )
    assert response.status_code == 409
    assert "already exists" in response.text.lower()


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, existing_user: User):
    response = await client.post(
        "/api/v1/auth/login", json={"email": "existing@example.com", "password": "password123"}
    )
    assert response.status_code == 200
    assert "access_token" in response.cookies


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient, existing_user: User):
    response = await client.post(
        "/api/v1/auth/login", json={"email": "existing@example.com", "password": "wrongpassword"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_current_user_unauthorized(client: AsyncClient):
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_current_user_authorized(client: AsyncClient, existing_user: User):
    # Login first
    await client.post(
        "/api/v1/auth/login", json={"email": "existing@example.com", "password": "password123"}
    )

    # Get current user
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 200
    assert response.json()["email"] == "existing@example.com"
    assert response.json()["full_name"] == "Existing User"


@pytest.mark.asyncio
async def test_logout(client: AsyncClient, existing_user: User):
    # Login first
    await client.post(
        "/api/v1/auth/login", json={"email": "existing@example.com", "password": "password123"}
    )
    assert "access_token" in client.cookies

    # Logout
    response = await client.post("/api/v1/auth/logout")
    assert response.status_code == 200

    # Verify cookies are cleared
    assert not client.cookies.get("access_token")
    assert not client.cookies.get("refresh_token")
